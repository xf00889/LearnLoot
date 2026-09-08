import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


JsonObject = dict[str, Any]
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class HttpClientError(RuntimeError):
    pass


class HttpResponseError(HttpClientError):
    pass


@dataclass(frozen=True, slots=True)
class JsonHttpClient:
    timeout_seconds: float = 10.0
    max_retries: int = 2
    backoff_seconds: float = 0.25
    max_response_bytes: int = 5_000_000
    max_retry_after_seconds: float = 60.0
    user_agent: str = "LearnLoot/1.0"
    sleep: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")
        if self.max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be greater than zero")
        if self.max_retry_after_seconds < 0:
            raise ValueError("max_retry_after_seconds cannot be negative")

    def get_json(
        self,
        url: str,
        headers: Mapping[str, str] | None = None,
    ) -> JsonObject:
        request_headers = dict(headers or {})
        if not any(key.lower() == "user-agent" for key in request_headers):
            request_headers["User-Agent"] = self.user_agent

        request = Request(url=url, headers=request_headers, method="GET")

        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = response.read(self.max_response_bytes + 1)
                    if len(payload) > self.max_response_bytes:
                        raise HttpResponseError("provider response exceeded the configured size limit")

                    charset = response.headers.get_content_charset() or "utf-8"
                    try:
                        decoded = payload.decode(charset)
                    except (LookupError, UnicodeDecodeError) as exc:
                        raise HttpResponseError("provider response encoding was invalid") from exc

                    try:
                        document = json.loads(decoded)
                    except json.JSONDecodeError as exc:
                        raise HttpResponseError("provider response was not valid JSON") from exc

                    if not isinstance(document, dict):
                        raise HttpResponseError("provider JSON response must be an object")

                    return document

            except HTTPError as exc:
                if exc.code in _RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                    self.sleep(self._retry_delay(attempt, exc.headers.get("Retry-After")))
                    continue
                raise HttpClientError(f"provider request returned HTTP {exc.code}") from exc
            except URLError as exc:
                if attempt < self.max_retries:
                    self.sleep(self._retry_delay(attempt, None))
                    continue
                raise HttpClientError("provider request failed") from exc

        raise HttpClientError("provider request exhausted retry policy")

    def _retry_delay(self, attempt: int, retry_after: str | None) -> float:
        if retry_after:
            try:
                value = float(retry_after)
            except ValueError:
                value = -1
            if value >= 0:
                return min(value, self.max_retry_after_seconds)

        return self.backoff_seconds * (2**attempt)