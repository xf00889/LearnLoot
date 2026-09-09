from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import logging

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.http import HttpRequest

from tracking.services import normalize_attribution

from .models import ShoppingClickEvent, ShoppingProduct
from .validators import validate_https_affiliate_url

logger = logging.getLogger(__name__)


class ShoppingDestinationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ShoppingDestination:
    url: str


def resolve_shopping_destination(product: ShoppingProduct) -> ShoppingDestination:
    try:
        validate_https_affiliate_url(product.affiliate_url)
    except Exception as exc:
        raise ShoppingDestinationError("Shopping destination is not a valid HTTPS URL.") from exc
    return ShoppingDestination(url=product.affiliate_url.strip())


def _dedupe_cache_key(request: HttpRequest, product: ShoppingProduct) -> str | None:
    remote_addr = str(request.META.get("REMOTE_ADDR") or "").strip()
    if not remote_addr:
        return None
    secret = str(settings.SECRET_KEY).encode("utf-8")
    digest = hmac.new(
        secret,
        f"{remote_addr}|shopping|{product.pk}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"learnloot:shopping-click:{product.pk}:{digest}"


def record_shopping_click_event(*, request: HttpRequest, product: ShoppingProduct) -> bool:
    source = normalize_attribution(
        request.GET.get("source"),
        default="shopping_page",
        max_length=50,
    )
    campaign = normalize_attribution(request.GET.get("campaign"), max_length=100)

    dedupe_seconds = max(
        int(getattr(settings, "LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS", 2)),
        0,
    )
    cache_key = _dedupe_cache_key(request, product) if dedupe_seconds else None
    if cache_key is not None:
        try:
            if not cache.add(cache_key, 1, timeout=dedupe_seconds):
                return False
        except Exception:
            logger.exception("Shopping click dedupe cache failed for product_id=%s", product.pk)

    try:
        ShoppingClickEvent.objects.create(product=product, source=source, campaign=campaign)
    except DatabaseError:
        if cache_key is not None:
            try:
                cache.delete(cache_key)
            except Exception:
                logger.exception("Shopping click dedupe cleanup failed for product_id=%s", product.pk)
        logger.exception("Shopping click analytics write failed for product_id=%s", product.pk)
        return False

    return True
