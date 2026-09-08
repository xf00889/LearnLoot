from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import logging
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.http import HttpRequest

from courses.models import Course

from .models import AffiliateLink, ClickEvent

logger = logging.getLogger(__name__)
_TAG_RE = re.compile(r"[^a-z0-9._-]+")


class OutboundDestinationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class OutboundDestination:
    url: str
    kind: str
    affiliate_link: AffiliateLink | None

    @property
    def is_affiliate(self) -> bool:
        return self.kind == ClickEvent.DestinationKind.AFFILIATE


def _validated_https_url(value: str) -> str:
    url = str(value or "").strip()
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise OutboundDestinationError("Outbound destination is not a valid HTTPS URL.")
    return url


def active_affiliate_link(course: Course) -> AffiliateLink | None:
    prefetched = getattr(course, "public_affiliate_links", None)
    if prefetched is not None:
        return prefetched[0] if prefetched else None
    return (
        course.affiliate_links.filter(status=AffiliateLink.Status.ACTIVE)
        .order_by("-updated_at", "-id")
        .first()
    )


def resolve_outbound_destination(course: Course) -> OutboundDestination:
    affiliate = active_affiliate_link(course)
    if affiliate is not None:
        try:
            url = _validated_https_url(affiliate.url)
        except OutboundDestinationError:
            logger.warning(
                "Ignoring invalid active affiliate destination for course_id=%s link_id=%s",
                course.pk,
                affiliate.pk,
            )
        else:
            return OutboundDestination(
                url=url,
                kind=ClickEvent.DestinationKind.AFFILIATE,
                affiliate_link=affiliate,
            )

    return OutboundDestination(
        url=_validated_https_url(course.canonical_url),
        kind=ClickEvent.DestinationKind.PROVIDER,
        affiliate_link=None,
    )


def normalize_attribution(
    value: object,
    *,
    default: str = "",
    max_length: int,
) -> str:
    text = str(value or "").strip().lower()
    text = _TAG_RE.sub("-", text).strip("-._")
    return (text or default)[:max_length]


def _dedupe_cache_key(request: HttpRequest, course: Course) -> str | None:
    remote_addr = str(request.META.get("REMOTE_ADDR") or "").strip()
    if not remote_addr:
        return None
    secret = str(settings.SECRET_KEY).encode("utf-8")
    digest = hmac.new(
        secret,
        f"{remote_addr}|{course.pk}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"learnloot:outbound-click:{course.pk}:{digest}"


def record_click_event(
    *,
    request: HttpRequest,
    course: Course,
    destination: OutboundDestination,
) -> bool:
    source = normalize_attribution(
        request.GET.get("source"),
        default="course_page",
        max_length=50,
    )
    campaign = normalize_attribution(
        request.GET.get("campaign"),
        max_length=100,
    )

    dedupe_seconds = max(
        int(getattr(settings, "LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS", 2)),
        0,
    )
    cache_key = _dedupe_cache_key(request, course) if dedupe_seconds else None
    if cache_key is not None:
        try:
            if not cache.add(cache_key, 1, timeout=dedupe_seconds):
                return False
        except Exception:
            logger.exception(
                "Outbound click dedupe cache failed for course_id=%s",
                course.pk,
            )

    try:
        ClickEvent.objects.create(
            course=course,
            affiliate_link=destination.affiliate_link,
            destination_kind=destination.kind,
            source=source,
            campaign=campaign,
        )
    except DatabaseError:
        if cache_key is not None:
            try:
                cache.delete(cache_key)
            except Exception:
                logger.exception(
                    "Outbound click dedupe cache cleanup failed for course_id=%s",
                    course.pk,
                )
        logger.exception(
            "Outbound click analytics write failed for course_id=%s",
            course.pk,
        )
        return False
    return True
