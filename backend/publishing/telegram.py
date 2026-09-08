from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
import socket
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from courses.models import Course


TELEGRAM_MAX_MESSAGE_LENGTH = 4096
_MAX_RESPONSE_BYTES = 1024 * 1024


class TelegramDeliveryError(RuntimeError):
    """Base class for safe-to-log Telegram delivery errors."""


class TelegramConfigurationError(TelegramDeliveryError):
    pass


class TelegramRateLimitError(TelegramDeliveryError):
    def __init__(self, message: str, *, retry_after: int):
        super().__init__(message)
        self.retry_after = max(int(retry_after), 1)


class TelegramPermanentError(TelegramDeliveryError):
    pass


class TelegramAmbiguousError(TelegramDeliveryError):
    """The request outcome cannot be proven, so automatic retry is unsafe."""


@dataclass(frozen=True, slots=True)
class TelegramConfig:
    enabled: bool
    bot_token: str
    chat_id: str
    api_base_url: str
    timeout_seconds: float
    max_retries: int
    retry_base_seconds: int
    stale_send_minutes: int
    public_base_url: str


@dataclass(frozen=True, slots=True)
class TelegramSendResult:
    message_id: int


def get_telegram_config() -> TelegramConfig:
    return TelegramConfig(
        enabled=bool(settings.LEARNLOOT_TELEGRAM_ENABLED),
        bot_token=str(settings.LEARNLOOT_TELEGRAM_BOT_TOKEN).strip(),
        chat_id=str(settings.LEARNLOOT_TELEGRAM_CHAT_ID).strip(),
        api_base_url=str(settings.LEARNLOOT_TELEGRAM_API_BASE_URL).rstrip("/"),
        timeout_seconds=float(settings.LEARNLOOT_TELEGRAM_TIMEOUT_SECONDS),
        max_retries=max(int(settings.LEARNLOOT_TELEGRAM_MAX_RETRIES), 0),
        retry_base_seconds=max(int(settings.LEARNLOOT_TELEGRAM_RETRY_BASE_SECONDS), 1),
        stale_send_minutes=max(int(settings.LEARNLOOT_TELEGRAM_STALE_SEND_MINUTES), 1),
        public_base_url=str(settings.LEARNLOOT_PUBLIC_BASE_URL).rstrip("/"),
    )


def telegram_publication_enabled() -> bool:
    return get_telegram_config().enabled


def validate_telegram_config(config: TelegramConfig) -> None:
    if not config.enabled:
        return
    if not config.bot_token:
        raise TelegramConfigurationError("Telegram bot token is not configured.")
    if not config.chat_id:
        raise TelegramConfigurationError("Telegram chat id is not configured.")
    if not config.api_base_url.startswith("https://"):
        raise TelegramConfigurationError("Telegram API base URL must use HTTPS.")
    if not config.public_base_url.startswith(("https://", "http://")):
        raise TelegramConfigurationError("LearnLoot public base URL is invalid.")


def build_course_landing_url(
    course: Course,
    *,
    public_base_url: str | None = None,
) -> str:
    base = (public_base_url or get_telegram_config().public_base_url).rstrip("/")
    provider_slug = quote(course.provider.slug, safe="")
    course_slug = quote(course.slug, safe="")
    return f"{base}/courses/{provider_slug}/{course_slug}"


def _format_rating(course: Course) -> str | None:
    if course.rating is None:
        return None
    return f"{course.rating:.2f}".rstrip("0").rstrip(".")


def _format_duration(minutes: int | None) -> str | None:
    if minutes is None or minutes <= 0:
        return None
    hours, remainder = divmod(minutes, 60)
    if hours and remainder:
        return f"{hours}h {remainder}m"
    if hours:
        return f"{hours}h"
    return f"{remainder}m"


def render_telegram_course_message(
    course: Course,
    *,
    landing_url: str | None = None,
) -> str:
    landing_url = landing_url or build_course_landing_url(course)
    title = escape(course.title.strip()[:500])
    provider_name = escape(course.provider.name.strip()[:120])
    instructor = escape(course.instructor_name.strip()[:180]) if course.instructor_name else ""

    lines = [
        f"ðŸŽ“ <b>{title}</b>",
        "ðŸ”¥ <b>FREE COURSE</b>",
        "",
    ]

    rating = _format_rating(course)
    if rating is not None and course.review_count is not None:
        lines.append(f"â­ {escape(rating)}/5 Â· {course.review_count:,} reviews")
    elif rating is not None:
        lines.append(f"â­ {escape(rating)}/5")
    elif course.review_count is not None:
        lines.append(f"â­ {course.review_count:,} reviews")

    if instructor:
        lines.append(f"ðŸ‘¤ {instructor}")

    duration = _format_duration(course.duration_minutes)
    if duration is not None:
        lines.append(f"â± {escape(duration)}")

    if provider_name:
        lines.append(f"ðŸ« {provider_name}")

    lines.extend(
        [
            "",
            f'ðŸ‘‰ <a href="{escape(landing_url, quote=True)}">View on LearnLoot</a>',
        ]
    )

    message = "\n".join(lines).strip()
    if len(message) > TELEGRAM_MAX_MESSAGE_LENGTH:
        raise TelegramPermanentError("Rendered Telegram message exceeds the maximum length.")
    return message


def _sanitize_error(
    value: object,
    *,
    bot_token: str,
    chat_id: str,
) -> str:
    text = str(value or "").strip()
    if bot_token:
        text = text.replace(bot_token, "[REDACTED_TOKEN]")
    if chat_id:
        text = text.replace(chat_id, "[REDACTED_CHAT]")
    return text[:1000] or "Telegram request failed."


def _decode_json(raw: bytes) -> dict:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TelegramAmbiguousError("Telegram returned an unreadable response.") from exc
    if not isinstance(payload, dict):
        raise TelegramAmbiguousError("Telegram returned an unexpected response.")
    return payload


def _raise_api_error(
    payload: dict,
    *,
    bot_token: str,
    chat_id: str,
    fallback_code: int | None = None,
) -> None:
    code_value = payload.get("error_code", fallback_code or 0)
    try:
        error_code = int(code_value or 0)
    except (TypeError, ValueError):
        error_code = int(fallback_code or 0)

    description = _sanitize_error(
        payload.get("description", "Telegram API rejected the request."),
        bot_token=bot_token,
        chat_id=chat_id,
    )
    parameters = payload.get("parameters")
    retry_after = None
    if isinstance(parameters, dict):
        try:
            retry_after = int(parameters.get("retry_after") or 0)
        except (TypeError, ValueError):
            retry_after = None

    if error_code == 429:
        raise TelegramRateLimitError(
            f"Telegram rate limit: {description}",
            retry_after=retry_after or 1,
        ) from None

    if error_code >= 500:
        raise TelegramAmbiguousError(
            f"Telegram server error with ambiguous delivery outcome: {description}"
        ) from None

    raise TelegramPermanentError(
        f"Telegram rejected the message: {description}"
    ) from None


class TelegramBotClient:
    def __init__(
        self,
        config: TelegramConfig,
        *,
        opener: Callable[..., object] = urlopen,
    ):
        self.config = config
        self._opener = opener
        validate_telegram_config(config)

    def send_message(self, text: str) -> TelegramSendResult:
        if not text or len(text) > TELEGRAM_MAX_MESSAGE_LENGTH:
            raise TelegramPermanentError("Telegram message length is invalid.")

        endpoint = (
            f"{self.config.api_base_url}/bot{self.config.bot_token}/sendMessage"
        )
        body = urlencode(
            {
                "chat_id": self.config.chat_id,
                "text": text,
                "parse_mode": "HTML",
            }
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "LearnLootBot/0.1",
            },
        )

        try:
            response = self._opener(
                request,
                timeout=self.config.timeout_seconds,
            )
            with response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            try:
                raw = exc.read(_MAX_RESPONSE_BYTES + 1)
            except Exception:
                raw = b""
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise TelegramAmbiguousError(
                    "Telegram error response exceeded the safe size limit."
                ) from None
            if raw:
                try:
                    payload = _decode_json(raw)
                except TelegramAmbiguousError:
                    payload = {
                        "error_code": exc.code,
                        "description": "Telegram returned an unreadable error response.",
                    }
            else:
                payload = {
                    "error_code": exc.code,
                    "description": "Telegram returned an empty error response.",
                }
            _raise_api_error(
                payload,
                bot_token=self.config.bot_token,
                chat_id=self.config.chat_id,
                fallback_code=exc.code,
            )
            raise AssertionError("unreachable")
        except (URLError, TimeoutError, socket.timeout, OSError) as exc:
            safe = _sanitize_error(
                exc,
                bot_token=self.config.bot_token,
                chat_id=self.config.chat_id,
            )
            raise TelegramAmbiguousError(
                f"Telegram network failure with ambiguous delivery outcome: {safe}"
            ) from None

        if len(raw) > _MAX_RESPONSE_BYTES:
            raise TelegramAmbiguousError(
                "Telegram response exceeded the safe size limit."
            )

        payload = _decode_json(raw)
        if payload.get("ok") is not True:
            _raise_api_error(
                payload,
                bot_token=self.config.bot_token,
                chat_id=self.config.chat_id,
            )

        result = payload.get("result")
        if not isinstance(result, dict):
            raise TelegramAmbiguousError("Telegram success response did not contain a message.")

        try:
            message_id = int(result["message_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise TelegramAmbiguousError(
                "Telegram success response did not contain a valid message id."
            ) from exc

        return TelegramSendResult(message_id=message_id)