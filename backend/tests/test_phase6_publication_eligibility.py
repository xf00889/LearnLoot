from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone

from courses.admin import CourseAdmin
from courses.models import Course
from discovery.models import DiscoveryRun
from discovery.tasks import run_provider_discovery
from pricing.models import CoursePrice
from providers.admin import ProviderAdmin
from providers.models import Provider
from publishing.admin import AdminOverrideAdmin, PublicationQueueItemAdmin
from publishing.models import AdminOverride, DealEligibility, PublicationQueueItem
from publishing.services import (
    PublicationRules,
    calculate_deal_score,
    evaluate_course_for_publication,
    evaluate_provider_courses,
)
from publishing.tasks import (
    evaluate_course_publication_candidate,
    evaluate_provider_publication_candidates,
)


@pytest.fixture
def rules():
    return PublicationRules(
        min_rating=Decimal("4.00"),
        min_reviews=100,
        min_score=70,
        max_course_age=timedelta(hours=24),
        cooldown=timedelta(hours=168),
    )


@pytest.fixture
def provider(db):
    return Provider.objects.create(name="Udemy", slug="udemy")


@pytest.fixture
def high_quality_course(provider):
    now = timezone.now()
    course = Course.objects.create(
        provider=provider,
        external_id="slug:high-quality",
        title="High Quality Course",
        slug="high-quality-course",
        canonical_url="https://www.udemy.com/course/high-quality/",
        thumbnail_url="https://img.example/course.jpg",
        instructor_name="Example Instructor",
        rating=Decimal("4.50"),
        review_count=5_000,
        student_count=25_000,
        duration_minutes=180,
        description="A complete public course description.",
        last_checked_at=now,
        last_seen_at=now,
    )
    CoursePrice.objects.create(
        course=course,
        amount=Decimal("0.00"),
        currency="USD",
        is_free=True,
        price_type="free",
        observed_at=now,
        source_url=course.canonical_url,
    )
    return course


@pytest.mark.django_db
def test_high_quality_recent_free_course_is_scored_and_queued(high_quality_course, rules):
    result = evaluate_course_for_publication(high_quality_course, rules=rules)

    assert result.eligible is True
    assert result.queue_created is True
    assert result.score >= rules.min_score
    assert result.reasons == ()

    eligibility = DealEligibility.objects.get(course=high_quality_course)
    assert eligibility.eligible is True
    assert eligibility.score == result.score
    assert eligibility.latest_price.is_free is True

    queued = PublicationQueueItem.objects.get(course=high_quality_course)
    assert queued.status == PublicationQueueItem.Status.QUEUED
    assert queued.score == result.score


@pytest.mark.django_db
def test_score_is_deterministic_for_same_course_state(high_quality_course):
    latest = high_quality_course.prices.order_by("-observed_at", "-pk").first()

    first = calculate_deal_score(high_quality_course, latest)
    second = calculate_deal_score(high_quality_course, latest)

    assert first == second
    assert 0 <= first <= 100


@pytest.mark.django_db
def test_low_quality_course_is_not_queued(provider, rules):
    now = timezone.now()
    course = Course.objects.create(
        provider=provider,
        external_id="slug:low-quality",
        title="Low Quality",
        slug="low-quality",
        canonical_url="https://www.udemy.com/course/low-quality/",
        rating=Decimal("3.00"),
        review_count=10,
        last_checked_at=now,
    )
    CoursePrice.objects.create(
        course=course,
        amount=Decimal("0.00"),
        currency="USD",
        is_free=True,
        price_type="free",
        observed_at=now,
    )

    result = evaluate_course_for_publication(course, rules=rules)

    assert result.eligible is False
    assert "rating_below_minimum" in result.reasons
    assert "review_count_below_minimum" in result.reasons
    assert PublicationQueueItem.objects.filter(course=course).exists() is False


@pytest.mark.django_db
def test_force_eligible_bypasses_quality_and_cooldown_but_not_safety(provider, rules):
    now = timezone.now()
    course = Course.objects.create(
        provider=provider,
        external_id="slug:forced",
        title="Forced Course",
        slug="forced-course",
        canonical_url="https://www.udemy.com/course/forced/",
        rating=Decimal("2.00"),
        review_count=1,
        last_checked_at=now,
    )
    price = CoursePrice.objects.create(
        course=course,
        amount=Decimal("0.00"),
        currency="USD",
        is_free=True,
        price_type="free",
        observed_at=now,
    )
    PublicationQueueItem.objects.create(
        course=course,
        latest_price=price,
        score=90,
        status=PublicationQueueItem.Status.SENT,
        queued_at=now - timedelta(hours=2),
        sent_at=now - timedelta(hours=1),
    )
    AdminOverride.objects.create(
        course=course,
        decision=AdminOverride.Decision.FORCE_ELIGIBLE,
        note="Operator approved this deal.",
    )

    result = evaluate_course_for_publication(course, rules=rules, now=now)

    assert result.eligible is True
    assert result.override_applied is True
    assert result.reasons == ("admin_force_eligible",)
    assert result.queue_created is True

    course.status = Course.Status.HIDDEN
    course.save(update_fields=("status",))
    second = evaluate_course_for_publication(course, rules=rules, now=now)

    assert second.eligible is False
    assert "course_not_active" in second.reasons
    assert PublicationQueueItem.objects.filter(
        course=course,
        status=PublicationQueueItem.Status.QUEUED,
    ).exists() is False


@pytest.mark.django_db
def test_force_ineligible_blocks_high_quality_course(high_quality_course, rules):
    AdminOverride.objects.create(
        course=high_quality_course,
        decision=AdminOverride.Decision.FORCE_INELIGIBLE,
    )

    result = evaluate_course_for_publication(high_quality_course, rules=rules)

    assert result.eligible is False
    assert result.override_applied is True
    assert result.reasons == ("admin_force_ineligible",)
    assert PublicationQueueItem.objects.filter(course=high_quality_course).exists() is False


@pytest.mark.django_db
def test_recent_sent_item_enforces_publication_cooldown(high_quality_course, rules):
    now = timezone.now()
    price = high_quality_course.prices.first()
    PublicationQueueItem.objects.create(
        course=high_quality_course,
        latest_price=price,
        score=95,
        status=PublicationQueueItem.Status.SENT,
        queued_at=now - timedelta(hours=2),
        sent_at=now - timedelta(hours=1),
    )

    result = evaluate_course_for_publication(high_quality_course, rules=rules, now=now)

    assert result.eligible is False
    assert result.reasons == ("publication_cooldown",)


@pytest.mark.django_db
def test_repeated_evaluation_does_not_duplicate_queued_item(high_quality_course, rules):
    first = evaluate_course_for_publication(high_quality_course, rules=rules)
    second = evaluate_course_for_publication(high_quality_course, rules=rules)

    assert first.queue_created is True
    assert second.queue_created is False
    assert second.queue_item_id == first.queue_item_id
    assert PublicationQueueItem.objects.filter(
        course=high_quality_course,
        status=PublicationQueueItem.Status.QUEUED,
    ).count() == 1


@pytest.mark.django_db
def test_paid_price_change_cancels_existing_queued_item(high_quality_course, rules):
    first = evaluate_course_for_publication(high_quality_course, rules=rules)
    assert first.queue_created is True

    now = timezone.now()
    CoursePrice.objects.create(
        course=high_quality_course,
        amount=Decimal("19.99"),
        currency="USD",
        is_free=False,
        price_type="paid",
        observed_at=now,
    )
    high_quality_course.last_checked_at = now
    high_quality_course.save(update_fields=("last_checked_at",))

    second = evaluate_course_for_publication(high_quality_course, rules=rules, now=now)

    assert second.eligible is False
    assert "price_not_free" in second.reasons
    queue_item = PublicationQueueItem.objects.get(pk=first.queue_item_id)
    assert queue_item.status == PublicationQueueItem.Status.CANCELLED


@pytest.mark.django_db
def test_stable_free_price_uses_last_checked_timestamp_for_freshness(
    high_quality_course,
    rules,
):
    old_price = high_quality_course.prices.first()
    old_price.observed_at = timezone.now() - timedelta(days=30)
    old_price.save(update_fields=("observed_at",))

    high_quality_course.last_checked_at = timezone.now()
    high_quality_course.save(update_fields=("last_checked_at",))

    result = evaluate_course_for_publication(high_quality_course, rules=rules)

    assert result.eligible is True
    assert "course_check_stale" not in result.reasons


@pytest.mark.django_db
def test_stale_course_check_is_absolute_publication_block(high_quality_course, rules):
    now = timezone.now()
    high_quality_course.last_checked_at = now - timedelta(hours=25)
    high_quality_course.save(update_fields=("last_checked_at",))
    AdminOverride.objects.create(
        course=high_quality_course,
        decision=AdminOverride.Decision.FORCE_ELIGIBLE,
    )

    result = evaluate_course_for_publication(high_quality_course, rules=rules, now=now)

    assert result.eligible is False
    assert "course_check_stale" in result.reasons
    assert result.override_applied is False


@pytest.mark.django_db
def test_provider_evaluation_reports_counts_and_queues(high_quality_course, rules):
    result = evaluate_provider_courses(high_quality_course.provider, rules=rules)

    assert result.provider_id == high_quality_course.provider_id
    assert result.courses_evaluated == 1
    assert result.eligible == 1
    assert result.ineligible == 0
    assert result.queued == 1


@pytest.mark.django_db
def test_publication_celery_tasks_use_database_only_services(high_quality_course, rules):
    provider_result = SimpleNamespace(
        provider_id=high_quality_course.provider_id,
        courses_evaluated=3,
        eligible=2,
        ineligible=1,
        queued=1,
    )
    course_result = SimpleNamespace(
        course_id=high_quality_course.pk,
        eligible=True,
        score=91,
        queue_item_id=44,
        queue_created=True,
        override_applied=False,
        reasons=(),
    )

    with patch(
        "publishing.tasks.evaluate_provider_courses",
        return_value=provider_result,
    ) as provider_evaluate:
        result = evaluate_provider_publication_candidates.run(
            high_quality_course.provider_id
        )
    provider_evaluate.assert_called_once()
    assert result["queued"] == 1

    with patch(
        "publishing.tasks.evaluate_course_for_publication",
        return_value=course_result,
    ) as course_evaluate:
        result = evaluate_course_publication_candidate.run(high_quality_course.pk)
    course_evaluate.assert_called_once()
    assert result["queue_item_id"] == 44
    assert result["eligible"] is True


@pytest.mark.django_db
def test_discovery_success_enqueues_publication_evaluation(provider):
    fake_run = SimpleNamespace(
        pk=501,
        status=DiscoveryRun.Status.SUCCEEDED,
        records_found=2,
        records_new=1,
        records_updated=1,
        records_failed=0,
    )
    target = SimpleNamespace(connector=object(), source="source-a")

    with patch("discovery.tasks.build_discovery_target", return_value=target), patch(
        "discovery.tasks.execute_discovery", return_value=fake_run
    ), patch(
        "discovery.tasks.evaluate_provider_publication_candidates.delay"
    ) as publication_delay:
        result = run_provider_discovery.run(provider.pk)

    publication_delay.assert_called_once_with(provider.pk)
    assert result["status"] == DiscoveryRun.Status.SUCCEEDED


@pytest.mark.django_db
def test_course_admin_evaluation_action_only_enqueues_task(high_quality_course):
    model_admin = CourseAdmin(Course, admin.site)
    request = RequestFactory().post("/admin/courses/course/")

    with patch.object(model_admin, "message_user"), patch(
        "courses.admin.evaluate_course_publication_candidate.delay"
    ) as delay:
        model_admin.queue_publication_evaluation(
            request,
            Course.objects.filter(pk=high_quality_course.pk),
        )

    delay.assert_called_once_with(high_quality_course.pk)


@pytest.mark.django_db
def test_provider_admin_evaluation_action_only_enqueues_task(provider):
    model_admin = ProviderAdmin(Provider, admin.site)
    request = RequestFactory().post("/admin/providers/provider/")

    with patch.object(model_admin, "message_user"), patch(
        "providers.admin.evaluate_provider_publication_candidates.delay"
    ) as delay:
        model_admin.queue_publication_evaluation(
            request,
            Provider.objects.filter(pk=provider.pk),
        )

    delay.assert_called_once_with(provider.pk)


@pytest.mark.django_db
def test_course_hide_admin_action_cancels_queued_publication(high_quality_course, rules):
    result = evaluate_course_for_publication(high_quality_course, rules=rules)
    model_admin = CourseAdmin(Course, admin.site)
    request = RequestFactory().post("/admin/courses/course/")

    with patch.object(model_admin, "message_user"):
        model_admin.hide_selected(
            request,
            Course.objects.filter(pk=high_quality_course.pk),
        )

    queue_item = PublicationQueueItem.objects.get(pk=result.queue_item_id)
    assert queue_item.status == PublicationQueueItem.Status.CANCELLED


@pytest.mark.django_db
def test_provider_deactivation_admin_action_cancels_queued_publication(
    high_quality_course,
    rules,
):
    result = evaluate_course_for_publication(high_quality_course, rules=rules)
    model_admin = ProviderAdmin(Provider, admin.site)
    request = RequestFactory().post("/admin/providers/provider/")

    with patch.object(model_admin, "message_user"):
        model_admin.deactivate_selected_providers(
            request,
            Provider.objects.filter(pk=high_quality_course.provider_id),
        )

    queue_item = PublicationQueueItem.objects.get(pk=result.queue_item_id)
    assert queue_item.status == PublicationQueueItem.Status.CANCELLED


@pytest.mark.django_db
def test_override_admin_save_tracks_operator_and_re_evaluates(high_quality_course):
    user = get_user_model().objects.create_user(
        username="operator",
        password="not-used-in-test",
        is_staff=True,
    )
    override = AdminOverride(
        course=high_quality_course,
        decision=AdminOverride.Decision.FORCE_INELIGIBLE,
    )
    model_admin = AdminOverrideAdmin(AdminOverride, admin.site)
    request = RequestFactory().post("/admin/publishing/adminoverride/")
    request.user = user

    with patch("publishing.admin.evaluate_course_for_publication") as evaluate:
        model_admin.save_model(request, override, form=None, change=False)

    override.refresh_from_db()
    assert override.updated_by == user
    evaluate.assert_called_once()


def test_publication_queue_admin_is_not_directly_creatable_or_deletable():
    model_admin = PublicationQueueItemAdmin(PublicationQueueItem, admin.site)
    request = RequestFactory().get("/")

    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_delete_permission(request) is False
    assert PublicationQueueItemAdmin.cancel_queued_items.allowed_permissions == ["change"]