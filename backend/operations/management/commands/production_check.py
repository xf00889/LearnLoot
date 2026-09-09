from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


@dataclass(frozen=True, slots=True)
class ProductionIssue:
    code: str
    message: str


def _https_url(value: str) -> bool:
    parsed = urlsplit(str(value or "").strip())
    return parsed.scheme.lower() == "https" and bool(parsed.hostname)


def collect_production_issues() -> list[ProductionIssue]:
    issues: list[ProductionIssue] = []

    if getattr(settings, "LEARNLOOT_ENVIRONMENT", "") != "production":
        issues.append(
            ProductionIssue(
                "environment",
                "LEARNLOOT_ENVIRONMENT must be 'production'.",
            )
        )

    if settings.DEBUG:
        issues.append(ProductionIssue("debug", "DJANGO_DEBUG must be false."))

    secret = str(settings.SECRET_KEY or "")
    if len(secret) < 50 or secret.lower() in {"replace-me", "changeme"}:
        issues.append(
            ProductionIssue(
                "secret_key",
                "DJANGO_SECRET_KEY must be a strong production secret of at least 50 characters.",
            )
        )

    hosts = {str(host).strip().lower() for host in settings.ALLOWED_HOSTS}
    if not hosts or "*" in hosts or hosts.intersection({"localhost", "127.0.0.1", "::1"}):
        issues.append(
            ProductionIssue(
                "allowed_hosts",
                "DJANGO_ALLOWED_HOSTS must contain only explicit production hosts.",
            )
        )

    engine = str(settings.DATABASES["default"].get("ENGINE") or "")
    if "postgresql" not in engine:
        issues.append(
            ProductionIssue(
                "database",
                "Production DATABASE_URL must use PostgreSQL.",
            )
        )

    public_base = str(getattr(settings, "LEARNLOOT_PUBLIC_BASE_URL", ""))
    if not _https_url(public_base):
        issues.append(
            ProductionIssue(
                "public_base_url",
                "LEARNLOOT_PUBLIC_BASE_URL must be an absolute HTTPS URL.",
            )
        )

    if not settings.SECURE_SSL_REDIRECT:
        issues.append(
            ProductionIssue(
                "ssl_redirect",
                "DJANGO_SECURE_SSL_REDIRECT must be true.",
            )
        )
    if not settings.SESSION_COOKIE_SECURE:
        issues.append(
            ProductionIssue(
                "session_cookie",
                "DJANGO_SESSION_COOKIE_SECURE must be true.",
            )
        )
    if not settings.CSRF_COOKIE_SECURE:
        issues.append(
            ProductionIssue(
                "csrf_cookie",
                "DJANGO_CSRF_COOKIE_SECURE must be true.",
            )
        )
    if int(settings.SECURE_HSTS_SECONDS or 0) <= 0:
        issues.append(
            ProductionIssue(
                "hsts",
                "DJANGO_SECURE_HSTS_SECONDS must be greater than zero after HTTPS is verified.",
            )
        )

    cache_backend = str(settings.CACHES["default"].get("BACKEND") or "")
    if cache_backend != "django.core.cache.backends.redis.RedisCache":
        issues.append(
            ProductionIssue(
                "cache",
                "LEARNLOOT_CACHE_URL must configure Django's shared Redis cache.",
            )
        )

    if not getattr(settings, "LEARNLOOT_MEDIA_ROOT_CONFIGURED", False):
        issues.append(
            ProductionIssue(
                "media_root_config",
                "LEARNLOOT_MEDIA_ROOT must be explicitly configured for production.",
            )
        )

    if not getattr(settings, "LEARNLOOT_MEDIA_PERSISTENCE_CONFIRMED", False):
        issues.append(
            ProductionIssue(
                "media",
                "LEARNLOOT_MEDIA_PERSISTENCE_CONFIRMED must be true after persistent media storage and backups are configured.",
            )
        )

    media_root = Path(settings.MEDIA_ROOT)
    if not media_root.is_absolute():
        issues.append(
            ProductionIssue(
                "media_root",
                "LEARNLOOT_MEDIA_ROOT must resolve to an absolute persistent path.",
            )
        )

    if getattr(settings, "LEARNLOOT_TELEGRAM_ENABLED", False):
        if not str(getattr(settings, "LEARNLOOT_TELEGRAM_BOT_TOKEN", "")).strip():
            issues.append(
                ProductionIssue(
                    "telegram_token",
                    "Telegram is enabled but LEARNLOOT_TELEGRAM_BOT_TOKEN is empty.",
                )
            )
        if not str(getattr(settings, "LEARNLOOT_TELEGRAM_CHANNEL_ID", "")).strip():
            issues.append(
                ProductionIssue(
                    "telegram_channel",
                    "Telegram is enabled but LEARNLOOT_TELEGRAM_CHANNEL_ID is empty.",
                )
            )

    return issues


class Command(BaseCommand):
    help = "Fail closed unless LearnLoot's required production settings are configured."

    def handle(self, *args, **options):
        issues = collect_production_issues()
        if issues:
            for issue in issues:
                self.stderr.write(f"[{issue.code}] {issue.message}")
            raise CommandError(
                f"Production readiness failed with {len(issues)} issue(s)."
            )

        self.stdout.write("PHASE10_PRODUCTION_SETTINGS=PASS")
