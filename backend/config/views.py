import logging
import uuid

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


logger = logging.getLogger("learnloot.health")


def _no_store_json(payload: dict, *, status: int = 200) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _database_ready() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        logger.warning("Database readiness check failed: %s", type(exc).__name__)
        return False
    return True


def _cache_ready() -> bool:
    key = f"learnloot:readiness:{uuid.uuid4().hex}"
    try:
        cache.set(key, "ok", timeout=10)
        value = cache.get(key)
        cache.delete(key)
    except Exception as exc:
        logger.warning("Cache readiness check failed: %s", type(exc).__name__)
        return False
    return value == "ok"


@require_GET
def live(request):
    return _no_store_json({"status": "ok"})


@require_GET
def ready(request):
    database_ok = _database_ready()
    cache_ok = _cache_ready()
    checks = {
        "database": "ok" if database_ok else "unavailable",
        "cache": "ok" if cache_ok else "degraded",
    }

    if not database_ok:
        status = "unavailable"
        status_code = 503
    elif not cache_ok:
        # The site can still serve content and outbound redirects when the
        # analytics/dedupe cache is unavailable. Report degradation without
        # removing the web application from service.
        status = "degraded"
        status_code = 200
    else:
        status = "ok"
        status_code = 200

    return _no_store_json(
        {
            "status": status,
            "checks": checks,
        },
        status=status_code,
    )


@require_GET
def health(request):
    """Backward-compatible database-only health endpoint."""

    available = _database_ready()
    return _no_store_json(
        {
            "status": "ok" if available else "unavailable",
            "database": "ok" if available else "unavailable",
        },
        status=200 if available else 503,
    )
