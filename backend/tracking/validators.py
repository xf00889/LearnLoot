from urllib.parse import urlsplit

from django.core.exceptions import ValidationError


def validate_https_destination(value: str) -> None:
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValidationError("Outbound destinations must be absolute HTTPS URLs.")
