from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from courses.models import Course, CourseSource
from discovery.providers.base import ProviderAccessError
from discovery.providers.udemy_free import UdemyFreeConfig, UdemyFreeCourseProvider
from discovery.scrapy_app.runner import ScrapyCrawlerError
from discovery.udemy_catalog import UDEMY_DEFAULT_SEARCH_URL
from discovery.services import execute_discovery
from pricing.models import CoursePrice
from providers.models import Provider


SOURCE = UDEMY_DEFAULT_SEARCH_URL


class StubCrawler:
    def __init__(self, records):
        self.records = list(records)
        self.calls = []

    def crawl(self, source, *, max_pages, item_limit, render_wait_ms, language="en", exclude_urls=()):
        self.calls.append(
            {
                "source": source,
                "max_pages": max_pages,
                "item_limit": item_limit,
                "render_wait_ms": render_wait_ms,
                "language": language,
                "exclude_urls": tuple(exclude_urls),
            }
        )
        yield from self.records


def free_record(course_id="slug:free-python-basics", title="Free Python Basics"):
    return {
        "id": course_id,
        "identity_kind": "slug",
        "title": title,
        "url": "https://www.udemy.com/course/free-python-basics/",
        "image_480x270": "https://img-c.udemycdn.com/course/480x270/example.jpg",
        "visible_instructors": [{"display_name": "Ada Example"}],
        "avg_rating": "4.70",
        "num_reviews": 120,
        "num_subscribers": None,
        "headline": "",
        "is_paid": False,
        "catalog_kind": "free",
        "free_verified": True,
        "price_verification": "public_course_page",
        "source_url": SOURCE,
        "source_type": "udemy_free_catalog_scrapy",
    }


def build_connector(records, **overrides):
    crawler = StubCrawler(records)
    config = UdemyFreeConfig(
        access_approved=True,
        max_pages=overrides.pop("max_pages", 2),
        item_limit=overrides.pop("item_limit", 0),
        render_wait_ms=overrides.pop("render_wait_ms", 3500),
        **overrides,
    )
    return UdemyFreeCourseProvider(config, crawler=crawler), crawler


def test_udemy_provider_requires_explicit_access_acknowledgement():
    connector = UdemyFreeCourseProvider(UdemyFreeConfig())

    with pytest.raises(ProviderAccessError, match="not been acknowledged"):
        connector.validate_access()


def test_udemy_provider_accepts_only_public_free_catalog_source():
    connector, _crawler = build_connector([])

    with pytest.raises(ValueError, match="courses/free"):
        list(connector.discover("https://www.udemy.com/courses/development/"))

    with pytest.raises(ValueError, match="courses/free"):
        list(
            connector.discover(
                "https://www.udemy.com/courses/search/?q=python&price=price-free"
            )
        )


def test_udemy_provider_delegates_discovery_to_scrapy_runner():
    connector, crawler = build_connector([free_record()], max_pages=3, item_limit=10)

    records = list(connector.discover(SOURCE))

    assert len(records) == 1
    assert crawler.calls == [
        {
            "source": SOURCE,
            "max_pages": 3,
            "item_limit": 10,
            "render_wait_ms": 3500,
            "language": "en",
            "exclude_urls": (),
        }
    ]


def test_udemy_provider_filters_non_free_or_non_catalog_records():
    paid = free_record("slug:paid")
    paid["is_paid"] = True
    wrong_catalog = free_record("slug:wrong")
    wrong_catalog["catalog_kind"] = "discount"
    unverified = free_record("slug:unverified")
    unverified["free_verified"] = False

    connector, _crawler = build_connector([paid, wrong_catalog, unverified, free_record()])

    records = list(connector.discover(SOURCE))

    assert [record["id"] for record in records] == ["slug:free-python-basics"]


def test_udemy_provider_maps_scrapy_metadata_to_neutral_candidate():
    connector, _crawler = build_connector([])
    candidate = connector.parse(free_record(), SOURCE)

    assert candidate.external_id == "slug:free-python-basics"
    assert candidate.title == "Free Python Basics"
    assert candidate.canonical_url == "https://www.udemy.com/course/free-python-basics/"
    assert candidate.instructor_name == "Ada Example"
    assert candidate.rating == "4.70"
    assert candidate.review_count == 120
    assert candidate.price_amount == "0.00"
    assert candidate.currency == "USD"
    assert candidate.is_free is True
    assert candidate.price_type == "free"
    assert candidate.source_type == "udemy_free_catalog_scrapy"


def test_udemy_provider_refuses_to_reclassify_paid_or_ambiguous_record():
    connector, _crawler = build_connector([])

    paid = free_record()
    paid["is_paid"] = True
    with pytest.raises(ValueError, match="not explicitly marked"):
        connector.parse(paid, SOURCE)

    ambiguous = free_record()
    ambiguous.pop("catalog_kind")
    with pytest.raises(ValueError, match="free catalog"):
        connector.parse(ambiguous, SOURCE)

    unverified = free_record()
    unverified["free_verified"] = False
    with pytest.raises(ValueError, match="not verified free"):
        connector.parse(unverified, SOURCE)


def test_udemy_provider_does_not_use_retired_direct_course_api():
    connector, _crawler = build_connector([])

    with pytest.raises(ProviderAccessError, match="not enabled"):
        connector.fetch_course("12345")


@pytest.mark.django_db
def test_udemy_scrapy_provider_integrates_with_discovery_pipeline():
    provider = Provider.objects.create(name="Udemy", slug="udemy")
    connector, _crawler = build_connector([free_record()], max_pages=1)

    run = execute_discovery(provider, connector, SOURCE)

    assert run.records_found == 1
    assert run.records_new == 1
    assert run.records_updated == 0
    assert run.records_failed == 0

    course = Course.objects.get(provider=provider, external_id="slug:free-python-basics")
    assert course.canonical_url == "https://www.udemy.com/course/free-python-basics/"
    assert CourseSource.objects.filter(
        course=course,
        source_url=SOURCE,
        source_type="udemy_free_catalog_scrapy",
    ).exists()

    price = CoursePrice.objects.get(course=course)
    assert price.is_free is True
    assert str(price.amount) == "0.00"
    assert price.currency == "USD"


def test_udemy_smoke_command_requires_explicit_acknowledgement():
    with pytest.raises(CommandError, match="acknowledge-access-terms"):
        call_command("smoke_udemy_free", limit=1)


@pytest.mark.django_db
def test_udemy_smoke_command_is_read_only(capsys):
    record = free_record()

    with patch(
        "discovery.management.commands.smoke_udemy_free.UdemyFreeCourseProvider.discover",
        return_value=iter([record]),
    ):
        call_command("smoke_udemy_free", acknowledge_access_terms=True, limit=1)

    captured = capsys.readouterr()
    assert "UDEMY_FREE_SMOKE=PASS (1 courses)" in captured.out
    assert Course.objects.count() == 0


def test_udemy_smoke_command_reports_scrapy_block_cleanly():
    with patch(
        "discovery.management.commands.smoke_udemy_free.UdemyFreeCourseProvider.discover",
        side_effect=ScrapyCrawlerError("blocked"),
    ):
        with pytest.raises(CommandError, match="UDEMY_FREE_SMOKE=BLOCKED"):
            call_command("smoke_udemy_free", acknowledge_access_terms=True, limit=1)
