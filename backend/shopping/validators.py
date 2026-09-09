from urllib.parse import urlsplit

from django.core.exceptions import ValidationError


def validate_https_affiliate_url(value: str) -> None:
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValidationError("Affiliate destinations must be absolute HTTPS URLs.")
