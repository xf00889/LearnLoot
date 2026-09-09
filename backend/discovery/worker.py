import hashlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from django.conf import settings
from django.core.cache import cache


def _worker_revision() -> str:
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts or "migrations" in path.parts:
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def _worker_prefix() -> str:
    return f"learnloot-discovery-{_worker_revision()}@"


def _worker_nodes() -> set[str]:
    try:
        from config.celery import app

        return set((app.control.inspect(timeout=0.5).ping() or {}).keys())
    except Exception:
        return set()


def _stop_stale_local_workers(nodes: set[str]) -> None:
    from config.celery import app

    active = app.control.inspect(timeout=0.5).active() or {}
    if any(active.get(node) for node in nodes):
        raise RuntimeError("The local Celery worker is still processing a task.")

    app.control.shutdown(destination=sorted(nodes))
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not nodes.intersection(_worker_nodes()):
            return
        time.sleep(0.1)
    raise RuntimeError("The stale local Celery worker did not stop cleanly.")


def ensure_local_discovery_worker() -> str:
    """Start one fixed local worker when Django is running in development."""

    if not settings.DEBUG or not settings.LEARNLOOT_ADMIN_AUTO_START_CELERY_WORKER:
        return "external"
    nodes = _worker_nodes()
    worker_prefix = _worker_prefix()
    if any(node.startswith(worker_prefix) for node in nodes):
        return "available"
    local_hostname = socket.gethostname().lower()
    stale_nodes = {
        node
        for node in nodes
        if node.lower() == f"celery@{local_hostname}"
        or (
            node.startswith("learnloot-discovery-")
            and node.lower().endswith(f"@{local_hostname}")
        )
    }
    if stale_nodes:
        _stop_stale_local_workers(stale_nodes)
        cache.delete("learnloot:celery-worker-starting")
    if not cache.add("learnloot:celery-worker-starting", True, timeout=30):
        return "starting"

    command = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "config",
        "worker",
        "--loglevel=INFO",
        f"--logfile={settings.BASE_DIR / 'celery-worker.log'}",
        f"--hostname={worker_prefix}%h",
    ]
    options = {
        "cwd": str(settings.BASE_DIR),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        command.append("--pool=solo")
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        options["start_new_session"] = True

    try:
        subprocess.Popen(command, **options)
    except OSError:
        cache.delete("learnloot:celery-worker-starting")
        raise
    return "started"
