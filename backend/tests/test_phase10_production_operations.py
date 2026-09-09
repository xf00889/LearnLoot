from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse

from discovery.models import DiscoveryRun
from discovery.tasks import schedule_active_provider_discovery
from operations.management.commands.backup_postgres import build_pg_environment
from operations.management.commands.production_check import collect_production_issues
from providers.models import Provider


def test_liveness_endpoint_does_not_expose_dependency_details(client):
    response = client.get(reverse("health-live"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_readiness_endpoint_checks_database_and_cache(client):
    response = client.get(reverse("health-ready"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "database": "ok",
            "cache": "ok",
        },
    }
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_readiness_degrades_without_cache_but_keeps_serving(client, monkeypatch):
    monkeypatch.setattr("config.views._cache_ready", lambda: False)

    response = client.get(reverse("health-ready"))

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["cache"] == "degraded"


@pytest.mark.django_db
def test_readiness_fails_closed_when_database_is_unavailable(client, monkeypatch):
    monkeypatch.setattr("config.views._database_ready", lambda: False)

    response = client.get(reverse("health-ready"))

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert response.json()["checks"]["database"] == "unavailable"


@override_settings(
    LEARNLOOT_ENVIRONMENT="development",
    DEBUG=True,
    SECRET_KEY="replace-me",
    ALLOWED_HOSTS=["localhost"],
)
def test_production_check_rejects_development_settings():
    issue_codes = {issue.code for issue in collect_production_issues()}

    assert "environment" in issue_codes
    assert "debug" in issue_codes
    assert "secret_key" in issue_codes
    assert "allowed_hosts" in issue_codes


@override_settings(
    LEARNLOOT_ENVIRONMENT="production",
    DEBUG=False,
    SECRET_KEY="x" * 64,
    ALLOWED_HOSTS=["learnloot.example"],
    DATABASES={"default": {"ENGINE": "django.db.backends.postgresql"}},
    LEARNLOOT_PUBLIC_BASE_URL="https://learnloot.example",
    SECURE_SSL_REDIRECT=True,
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SECURE_HSTS_SECONDS=3600,
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": "redis://cache.example:6379/2",
        }
    },
    MEDIA_ROOT=Path.cwd().resolve() / "persistent-media",
    LEARNLOOT_MEDIA_ROOT_CONFIGURED=True,
    LEARNLOOT_MEDIA_PERSISTENCE_CONFIRMED=True,
    LEARNLOOT_TELEGRAM_ENABLED=False,
)
def test_production_check_accepts_required_baseline():
    assert collect_production_issues() == []


def test_backup_environment_keeps_password_out_of_command_arguments():
    env = build_pg_environment(
        {
            "HOST": "db.internal",
            "PORT": "5432",
            "USER": "learnloot",
            "PASSWORD": "private-secret",
        }
    )

    assert env["PGPASSWORD"] == "private-secret"
    assert env["PGHOST"] == "db.internal"

    ssl_env = build_pg_environment(
        {
            "HOST": "db.internal",
            "OPTIONS": {
                "sslmode": "require",
                "sslrootcert": "C:/certs/root.crt",
            },
        }
    )
    assert ssl_env["PGSSLMODE"] == "require"
    assert ssl_env["PGSSLROOTCERT"] == "C:/certs/root.crt"


@pytest.mark.django_db
def test_status_command_is_secret_free():
    output = io.StringIO()

    call_command("learnloot_status", stdout=output)

    rendered = output.getvalue()
    assert '"database": "ok"' in rendered
    assert "SECRET_KEY" not in rendered
    assert "BOT_TOKEN" not in rendered
    assert "DATABASE_URL" not in rendered


@pytest.mark.django_db
@override_settings(
    LEARNLOOT_DISCOVERY_RUNNING_STALE_MINUTES=90,
    LEARNLOOT_UDEMY_DISCOVERY_ACCESS_APPROVED=True,
)
def test_periodic_discovery_queues_ready_provider(monkeypatch):
    provider = Provider.objects.create(
        name="Udemy",
        slug="udemy",
        status=Provider.Status.ACTIVE,
    )
    queued_ids = []
    monkeypatch.setattr(
        "discovery.tasks.run_provider_discovery.delay",
        lambda provider_id: queued_ids.append(provider_id),
    )
    monkeypatch.setattr(
        "discovery.tasks.get_discovery_readiness",
        lambda selected: (selected.pk == provider.pk, "Ready"),
    )

    result = schedule_active_provider_discovery()

    assert result == {
        "queued": 1,
        "skipped_running": 0,
        "skipped_not_ready": 0,
    }
    assert queued_ids == [provider.pk]


@pytest.mark.django_db
@override_settings(
    LEARNLOOT_DISCOVERY_RUNNING_STALE_MINUTES=90,
    LEARNLOOT_UDEMY_DISCOVERY_ACCESS_APPROVED=True,
)
def test_periodic_discovery_does_not_overlap_recent_running_job(monkeypatch):
    provider = Provider.objects.create(
        name="Udemy",
        slug="udemy",
        status=Provider.Status.ACTIVE,
    )
    DiscoveryRun.objects.create(
        provider=provider,
        source="https://www.udemy.com/courses/free/",
        status=DiscoveryRun.Status.RUNNING,
    )
    queued_ids = []
    monkeypatch.setattr(
        "discovery.tasks.run_provider_discovery.delay",
        lambda provider_id: queued_ids.append(provider_id),
    )

    result = schedule_active_provider_discovery()

    assert result["queued"] == 0
    assert result["skipped_running"] == 1
    assert queued_ids == []


def test_phase10_celery_beat_schedule_names_are_stable():
    from config.settings import build_celery_beat_schedule

    schedule = build_celery_beat_schedule(
        enabled=True,
        discovery_interval_minutes=60,
        telegram_interval_minutes=5,
    )

    assert set(schedule) == {
        "learnloot-discovery-scheduler",
        "learnloot-telegram-stale-reconciliation",
        "learnloot-telegram-queue-dispatch",
    }
    assert schedule["learnloot-discovery-scheduler"]["schedule"] == 3600.0
    assert schedule["learnloot-telegram-queue-dispatch"]["schedule"] == 300.0
