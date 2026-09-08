from decimal import Decimal

import pytest

from courses.models import Course, CourseSource
from discovery.models import DiscoveryObservation, DiscoveryRun
from discovery.providers import FakeCourseProvider
from discovery.services import DiscoveryExecutionError, execute_discovery
from pricing.models import CoursePrice
from providers.models import Provider


def fake_record(
    *,
    external_id: str = "fake-101",
    title: str = "Python Fundamentals",
    amount: str = "0.00",
    is_free: bool = True,
    rating: str = "4.70",
    source_url: str = "https://example.test/deals/development",
):
    return {
        "course": {
            "id": external_id,
            "name": title,
            "url": f"https://provider.test/course/{external_id}",
            "thumbnail": f"https://provider.test/images/{external_id}.jpg",
            "instructor": "Example Instructor",
            "rating": rating,
            "reviews": 125,
            "students": 2400,
            "duration_minutes": 180,
            "description": "Provider-specific fake payload used for pipeline tests.",
        },
        "offer": {
            "amount": amount,
            "currency": "usd",
            "is_free": is_free,
            "type": "promotion",
        },
        "source_url": source_url,
        "source_type": "listing",
    }


@pytest.fixture
def provider():
    return Provider.objects.create(name="Fake Provider", slug="fake")


@pytest.mark.django_db
def test_fake_provider_runs_full_pipeline(provider):
    connector = FakeCourseProvider([fake_record()])

    run = execute_discovery(provider, connector, "https://example.test/deals")

    assert run.status == DiscoveryRun.Status.SUCCEEDED
    assert run.records_found == 1
    assert run.records_new == 1
    assert run.records_updated == 0
    assert run.records_failed == 0

    course = Course.objects.get(provider=provider, external_id="fake-101")
    assert course.title == "Python Fundamentals"
    assert course.rating == Decimal("4.70")
    assert course.status == Course.Status.ACTIVE
    assert CourseSource.objects.filter(course=course).count() == 1

    price = CoursePrice.objects.get(course=course)
    assert price.amount == Decimal("0.00")
    assert price.currency == "USD"
    assert price.is_free is True

    observation = DiscoveryObservation.objects.get(run=run)
    assert observation.course == course


@pytest.mark.django_db
def test_rediscovery_is_idempotent_for_course_source_and_price(provider):
    record = fake_record()

    first = execute_discovery(provider, FakeCourseProvider([record]), "source-a")
    second = execute_discovery(provider, FakeCourseProvider([record]), "source-a")

    assert first.records_new == 1
    assert second.records_new == 0
    assert second.records_updated == 0
    assert Course.objects.filter(provider=provider, external_id="fake-101").count() == 1

    course = Course.objects.get(provider=provider, external_id="fake-101")
    assert CourseSource.objects.filter(course=course).count() == 1
    assert CoursePrice.objects.filter(course=course).count() == 1
    assert DiscoveryObservation.objects.filter(course=course).count() == 2


@pytest.mark.django_db
def test_metadata_change_updates_course_but_preserves_stable_slug(provider):
    execute_discovery(provider, FakeCourseProvider([fake_record()]), "source-a")
    course = Course.objects.get(provider=provider, external_id="fake-101")
    original_slug = course.slug

    changed = fake_record(title="Advanced Python Fundamentals")
    run = execute_discovery(provider, FakeCourseProvider([changed]), "source-a")

    course.refresh_from_db()
    assert run.records_updated == 1
    assert course.title == "Advanced Python Fundamentals"
    assert course.slug == original_slug
    assert CoursePrice.objects.filter(course=course).count() == 1


@pytest.mark.django_db
def test_price_change_creates_history_and_counts_as_update(provider):
    paid = fake_record(amount="49.99", is_free=False)
    free = fake_record(amount="0", is_free=True)

    execute_discovery(provider, FakeCourseProvider([paid]), "source-a")
    run = execute_discovery(provider, FakeCourseProvider([free]), "source-a")

    course = Course.objects.get(provider=provider, external_id="fake-101")
    prices = list(CoursePrice.objects.filter(course=course).order_by("observed_at", "id"))

    assert run.records_updated == 1
    assert len(prices) == 2
    assert prices[0].amount == Decimal("49.99")
    assert prices[0].is_free is False
    assert prices[1].amount == Decimal("0.00")
    assert prices[1].is_free is True


@pytest.mark.django_db
def test_invalid_record_is_rejected_without_creating_course(provider):
    invalid = fake_record(title="")

    run = execute_discovery(provider, FakeCourseProvider([invalid]), "source-a")

    assert run.status == DiscoveryRun.Status.SUCCEEDED
    assert run.records_found == 1
    assert run.records_failed == 1
    assert run.records_new == 0
    assert Course.objects.count() == 0

    observation = DiscoveryObservation.objects.get(run=run)
    assert observation.external_id == "fake-101"
    assert observation.course is None


@pytest.mark.django_db
def test_mixed_run_keeps_valid_records_when_another_record_is_invalid(provider):
    valid = fake_record(external_id="valid-1")
    invalid = fake_record(external_id="invalid-1", title="")

    run = execute_discovery(provider, FakeCourseProvider([valid, invalid]), "source-a")

    assert run.records_found == 2
    assert run.records_new == 1
    assert run.records_failed == 1
    assert Course.objects.filter(provider=provider, external_id="valid-1").exists()
    assert not Course.objects.filter(provider=provider, external_id="invalid-1").exists()


@pytest.mark.django_db
def test_provider_failure_is_audited_without_deleting_existing_course(provider):
    existing = Course.objects.create(
        provider=provider,
        external_id="existing-1",
        title="Existing Course",
        slug="existing-course",
        canonical_url="https://provider.test/course/existing-1",
    )
    connector = FakeCourseProvider(discovery_error=RuntimeError("simulated provider outage"))

    with pytest.raises(DiscoveryExecutionError) as exc_info:
        execute_discovery(provider, connector, "source-a")

    run = DiscoveryRun.objects.get(pk=exc_info.value.run_id)
    assert run.status == DiscoveryRun.Status.FAILED
    assert run.records_found == 0
    assert Course.objects.filter(pk=existing.pk).exists()


@pytest.mark.django_db
def test_empty_result_does_not_archive_or_delete_existing_courses(provider):
    existing = Course.objects.create(
        provider=provider,
        external_id="existing-1",
        title="Existing Course",
        slug="existing-course",
        canonical_url="https://provider.test/course/existing-1",
    )

    run = execute_discovery(provider, FakeCourseProvider([]), "source-a")

    existing.refresh_from_db()
    assert run.status == DiscoveryRun.Status.SUCCEEDED
    assert run.records_found == 0
    assert existing.status == Course.Status.ACTIVE
    assert Course.objects.filter(pk=existing.pk).exists()


@pytest.mark.django_db
def test_admin_hidden_status_is_preserved_during_rediscovery(provider):
    execute_discovery(provider, FakeCourseProvider([fake_record()]), "source-a")
    course = Course.objects.get(provider=provider, external_id="fake-101")
    course.status = Course.Status.HIDDEN
    course.save(update_fields=("status",))

    execute_discovery(
        provider,
        FakeCourseProvider([fake_record(title="Updated Provider Title")]),
        "source-a",
    )

    course.refresh_from_db()
    assert course.title == "Updated Provider Title"
    assert course.status == Course.Status.HIDDEN


@pytest.mark.django_db
def test_connector_provider_mismatch_fails_before_processing_records(provider):
    provider.slug = "different-provider"
    provider.save(update_fields=("slug",))

    with pytest.raises(DiscoveryExecutionError) as exc_info:
        execute_discovery(provider, FakeCourseProvider([fake_record()]), "source-a")

    run = DiscoveryRun.objects.get(pk=exc_info.value.run_id)
    assert run.status == DiscoveryRun.Status.FAILED
    assert run.records_found == 0
    assert Course.objects.count() == 0