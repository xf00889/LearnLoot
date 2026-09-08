from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.test import Client, override_settings
from django.utils import timezone

from courses.models import Course
from pricing.models import CoursePrice
from providers.models import Provider
from publishing.delivery import _snapshot_defaults
from publishing.models import DealEligibility, PublicationQueueItem
from tracking.models import AffiliateLink, ClickEvent


@pytest.fixture(autouse=True)
def clear_tracking_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def provider(db):
    return Provider.objects.create(
        name="Udemy",
        slug="udemy",
        status=Provider.Status.ACTIVE,
    )


def make_public_course(
    provider,
    *,
    external_id="course-1",
    slug="python-fast-track",
    canonical_url=None,
    status=Course.Status.ACTIVE,
    eligible=True,
    is_free=True,
    amount=Decimal("0.00"),
    checked_at=None,
):
    checked_at = checked_at or timezone.now()
    course = Course.objects.create(
        provider=provider,
        external_id=external_id,
        title=f"Course {external_id}",
        slug=slug,
        canonical_url=canonical_url or f"https://www.udemy.com/course/{slug}/",
        rating=Decimal("4.70"),
        review_count=1500,
        status=status,
        last_seen_at=checked_at,
        last_checked_at=checked_at,
    )
    price = CoursePrice.objects.create(
        course=course,
        amount=amount,
        currency="USD",
        is_free=is_free,
        price_type="free" if is_free else "paid",
        observed_at=checked_at,
        source_url=course.canonical_url,
    )
    DealEligibility.objects.create(
        course=course,
        latest_price=price,
        score=90,
        eligible=eligible,
        evaluated_at=checked_at,
    )
    return course


@pytest.mark.django_db
@override_settings(LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS=0)
def test_provider_redirect_records_privacy_minimized_click(provider):
    course = make_public_course(provider)

    response = Client().get(
        f"/go/{provider.slug}/{course.slug}/?source=course_page&campaign=launch"
    )

    assert response.status_code == 302
    assert response["Location"] == course.canonical_url
    assert response["Cache-Control"] == "no-store, private"
    assert response["X-Robots-Tag"] == "noindex, nofollow"

    event = ClickEvent.objects.get()
    assert event.course == course
    assert event.destination_kind == ClickEvent.DestinationKind.PROVIDER
    assert event.affiliate_link is None
    assert event.source == "course_page"
    assert event.campaign == "launch"
    field_names = {field.name for field in ClickEvent._meta.fields}
    assert "ip_address" not in field_names
    assert "user_agent" not in field_names


@pytest.mark.django_db
@override_settings(LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS=0)
def test_active_affiliate_destination_overrides_provider_and_is_audited(provider):
    course = make_public_course(provider)
    affiliate = AffiliateLink.objects.create(
        course=course,
        url="https://affiliate.example/learnloot-python",
        network="Approved Network",
        status=AffiliateLink.Status.ACTIVE,
        note="Approved program destination",
    )

    response = Client().get(f"/go/{provider.slug}/{course.slug}/?source=telegram")

    assert response.status_code == 302
    assert response["Location"] == affiliate.url
    event = ClickEvent.objects.get()
    assert event.affiliate_link == affiliate
    assert event.destination_kind == ClickEvent.DestinationKind.AFFILIATE
    assert event.source == "telegram"

    api = Client().get(f"/api/public/courses/{provider.slug}/{course.slug}/")
    assert api.status_code == 200
    payload = api.json()
    assert payload["outbound_is_affiliate"] is True
    assert payload["outbound_url"] == f"http://testserver/go/{provider.slug}/{course.slug}/"
    assert "provider_url" not in payload


@pytest.mark.django_db
def test_affiliate_links_require_https_and_only_one_active_per_course(provider):
    course = make_public_course(provider)
    invalid = AffiliateLink(
        course=course,
        url="javascript:alert(1)",
        status=AffiliateLink.Status.INACTIVE,
    )
    with pytest.raises(ValidationError):
        invalid.full_clean()

    AffiliateLink.objects.create(
        course=course,
        url="https://affiliate.example/one",
        status=AffiliateLink.Status.ACTIVE,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AffiliateLink.objects.create(
                course=course,
                url="https://affiliate.example/two",
                status=AffiliateLink.Status.ACTIVE,
            )


@pytest.mark.django_db
@override_settings(LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS=0)
def test_invalid_active_affiliate_fails_closed_to_valid_canonical_provider(provider):
    course = make_public_course(provider)
    affiliate = AffiliateLink.objects.create(
        course=course,
        url="https://affiliate.example/original",
        status=AffiliateLink.Status.ACTIVE,
    )
    AffiliateLink.objects.filter(pk=affiliate.pk).update(url="http://unsafe.example/plain-http")

    response = Client().get(f"/go/{provider.slug}/{course.slug}/")

    assert response.status_code == 302
    assert response["Location"] == course.canonical_url
    event = ClickEvent.objects.get()
    assert event.destination_kind == ClickEvent.DestinationKind.PROVIDER
    assert event.affiliate_link is None


@pytest.mark.django_db
def test_invalid_canonical_destination_is_not_public_or_redirected(provider):
    course = make_public_course(
        provider,
        canonical_url="http://unsafe.example/course",
    )

    assert Client().get(f"/go/{provider.slug}/{course.slug}/").status_code == 404
    assert (
        Client().get(f"/api/public/courses/{provider.slug}/{course.slug}/").status_code
        == 404
    )
    assert ClickEvent.objects.count() == 0


@pytest.mark.django_db
def test_outbound_endpoint_rechecks_public_course_safety(provider):
    paid = make_public_course(
        provider,
        external_id="paid",
        slug="paid",
        is_free=False,
        amount=Decimal("19.99"),
    )
    hidden = make_public_course(
        provider,
        external_id="hidden",
        slug="hidden",
        status=Course.Status.HIDDEN,
    )
    stale = make_public_course(
        provider,
        external_id="stale",
        slug="stale",
        checked_at=timezone.now() - timedelta(hours=25),
    )

    client = Client()
    for course in (paid, hidden, stale):
        assert client.get(f"/go/{provider.slug}/{course.slug}/").status_code == 404
    assert ClickEvent.objects.count() == 0


@pytest.mark.django_db
@override_settings(LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS=5)
def test_short_dedupe_window_does_not_block_redirect(provider):
    course = make_public_course(provider)
    client = Client(REMOTE_ADDR="203.0.113.9")

    first = client.get(f"/go/{provider.slug}/{course.slug}/")
    second = client.get(f"/go/{provider.slug}/{course.slug}/")

    assert first.status_code == second.status_code == 302
    assert ClickEvent.objects.count() == 1


@pytest.mark.django_db
@override_settings(LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS=0)
def test_attribution_is_normalized_and_bounded(provider):
    course = make_public_course(provider)

    Client().get(
        f"/go/{provider.slug}/{course.slug}/",
        {
            "source": " Telegram / Channel ",
            "campaign": "Launch Campaign !!! " + "x" * 150,
        },
    )

    event = ClickEvent.objects.get()
    assert event.source == "telegram-channel"
    assert event.campaign.startswith("launch-campaign-")
    assert len(event.campaign) == 100


@pytest.mark.django_db
@override_settings(LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS=0)
def test_analytics_database_failure_does_not_strand_visitor(provider):
    course = make_public_course(provider)

    with patch(
        "tracking.services.ClickEvent.objects.create",
        side_effect=DatabaseError("analytics unavailable"),
    ):
        response = Client().get(f"/go/{provider.slug}/{course.slug}/")

    assert response.status_code == 302
    assert response["Location"] == course.canonical_url


@pytest.mark.django_db
def test_telegram_snapshot_adds_source_and_campaign_for_outbound_attribution(provider):
    course = make_public_course(provider)
    latest_price = course.prices.first()
    queue_item = PublicationQueueItem.objects.create(
        course=course,
        latest_price=latest_price,
        score=90,
    )

    snapshot = _snapshot_defaults(
        queue_item,
        channel_id="@learnloot",
        public_base_url="https://learnloot.example",
    )

    assert snapshot["landing_url"].endswith(
        "/courses/udemy/python-fast-track?source=telegram&campaign=channel"
    )
    assert "source=telegram&amp;campaign=channel" in snapshot["message_text"]


def test_phase9_frontend_uses_tracked_outbound_route_and_disclosure():
    root = Path(__file__).resolve().parents[2]
    detail = (
        root
        / "frontend"
        / "src"
        / "app"
        / "courses"
        / "[provider]"
        / "[slug]"
        / "page.tsx"
    )
    api = root / "frontend" / "src" / "lib" / "api.ts"

    detail_text = detail.read_text(encoding="utf-8")
    api_text = api.read_text(encoding="utf-8")

    assert "course.outbound_url" in detail_text
    assert "resolvedSearchParams" in detail_text
    assert "source" in detail_text and "campaign" in detail_text
    assert "affiliate link" in detail_text
    assert "sponsored" in detail_text
    assert "provider_url" not in detail_text
    assert "outbound_url: string" in api_text
    assert "outbound_is_affiliate: boolean" in api_text
    assert "provider_url: string" not in api_text

def test_phase9_admin_registers_affiliate_links_and_read_only_click_events():
    from django.contrib import admin

    from tracking.admin import AffiliateLinkAdmin, ClickEventAdmin

    assert isinstance(admin.site._registry[AffiliateLink], AffiliateLinkAdmin)
    click_admin = admin.site._registry[ClickEvent]
    assert isinstance(click_admin, ClickEventAdmin)
    assert click_admin.has_add_permission(None) is False
    assert click_admin.has_delete_permission(None) is False
    assert set(click_admin.readonly_fields) >= {
        "course",
        "affiliate_link",
        "destination_kind",
        "source",
        "campaign",
        "occurred_at",
    }

