import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any


class ScrapyCrawlerError(RuntimeError):
    pass


class ScrapyUdemySource:
    """Run the Scrapy spider in an isolated subprocess and stream its JSONL items."""

    def __init__(
        self,
        *,
        python_executable: str | None = None,
        backend_dir: Path | None = None,
        run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        timeout_seconds: int = 300,
    ) -> None:
        self.python_executable = python_executable or sys.executable
        self.backend_dir = backend_dir or Path(__file__).resolve().parents[2]
        self._run = run
        self.timeout_seconds = timeout_seconds

    def crawl(
        self,
        source: str,
        *,
        max_pages: int,
        item_limit: int,
        render_wait_ms: int,
    ) -> Iterable[dict[str, Any]]:
        with tempfile.TemporaryDirectory(prefix="learnloot-udemy-scrapy-") as temp_dir:
            output_path = Path(temp_dir) / "courses.jsonl"
            command = [
                self.python_executable,
                "-m",
                "scrapy",
                "crawl",
                "udemy_free",
                "-a",
                f"source_url={source}",
                "-a",
                f"max_pages={max_pages}",
                "-a",
                f"item_limit={item_limit}",
                "-a",
                f"render_wait_ms={render_wait_ms}",
                "-O",
                str(output_path),
            ]

            environment = os.environ.copy()
            environment["SCRAPY_SETTINGS_MODULE"] = "discovery.scrapy_app.settings"
            existing_pythonpath = environment.get("PYTHONPATH", "")
            environment["PYTHONPATH"] = os.pathsep.join(
                value
                for value in (str(self.backend_dir), existing_pythonpath)
                if value
            )

            try:
                result = self._run(
                    command,
                    cwd=str(self.backend_dir),
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ScrapyCrawlerError(
                    "Udemy Scrapy crawl exceeded the configured timeout"
                ) from exc
            except OSError as exc:
                raise ScrapyCrawlerError(
                    "Udemy Scrapy crawl process could not be started"
                ) from exc

            if result.returncode != 0:
                raise ScrapyCrawlerError(
                    "Udemy Scrapy crawl failed; inspect Scrapy logs for the provider response"
                )

            if not output_path.exists():
                raise ScrapyCrawlerError("Udemy Scrapy crawl produced no feed output")

            with output_path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ScrapyCrawlerError(
                            f"Udemy Scrapy feed contains invalid JSON on line {line_number}"
                        ) from exc
                    if not isinstance(record, dict):
                        raise ScrapyCrawlerError(
                            f"Udemy Scrapy feed item {line_number} is not an object"
                        )
                    yield record