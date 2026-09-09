from __future__ import annotations

import json

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection

from courses.models import Course
from discovery.models import DiscoveryRun
from publishing.models import PublicationQueueItem, TelegramPost
from shopping.models import ShoppingClickEvent, ShoppingPost
from tracking.models import ClickEvent


def build_status() -> dict:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()

    cache_key = "learnloot:status-probe"
    try:
        cache.set(cache_key, "ok", timeout=10)
        cache_ok = cache.get(cache_key) == "ok"
        cache.delete(cache_key)
    except Exception:
        cache_ok = False

    latest = DiscoveryRun.objects.order_by("-started_at", "-pk").first()

    return {
        "database": "ok",
        "cache": "ok" if cache_ok else "unavailable",
        "courses": {
            "total": Course.objects.count(),
            "active": Course.objects.filter(status=Course.Status.ACTIVE).count(),
        },
        "discovery": {
            "latest_status": latest.status if latest else None,
            "latest_started_at": latest.started_at.isoformat() if latest else None,
        },
        "publication": {
            "queued": PublicationQueueItem.objects.filter(
                status=PublicationQueueItem.Status.QUEUED
            ).count(),
            "telegram_ambiguous": TelegramPost.objects.filter(
                status=TelegramPost.Status.AMBIGUOUS
            ).count(),
            "telegram_failed": TelegramPost.objects.filter(
                status=TelegramPost.Status.FAILED
            ).count(),
        },
        "shopping": {
            "published_posts": ShoppingPost.objects.filter(
                status=ShoppingPost.Status.PUBLISHED
            ).count(),
            "click_events": ShoppingClickEvent.objects.count(),
        },
        "course_click_events": ClickEvent.objects.count(),
    }


class Command(BaseCommand):
    help = "Print a secret-free operational snapshot for LearnLoot."

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(build_status(), sort_keys=True))
