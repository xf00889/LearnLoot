from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib import admin
from django.test import RequestFactory, override_settings

from courses.admin import (
    CourseAdmin,
    CoursePriceInline,
    CourseSourceInline,
    DealEligibilityInline,
    DiscoveryObservationInline as CourseObservationInline,
    PublicationQueueInline,
)
from courses.models import Course
from discovery.admin import DiscoveryRunAdmin
from discovery.models import DiscoveryRun
from discovery.providers.udemy_free import UdemyFreeCourseProvider
from discovery.registry import (
    UnsupportedDiscoveryProvider,
    build_discovery_target,
    get_discovery_readiness,
    safe_source_for_display,
)
from discovery.tasks import run_provider_discovery
from providers.admin import ProviderAdmin
from providers.models import Provider


READY_SETTINGS = {
    "LEARNLOOT_UDEMY_DISCOVERY_ACCESS_APPROVED": True,
    "LEARNLOOT_UDEMY_DISCOVERY_SOURCE_URL": "https://www.udemy.com/courses/free/",
    "LEARNLOOT_UDEMY_DISCOVERY_MAX_PAGES": 3,
    "LEARNLOOT_UDEMY_DISCOVERY_ITEM_LIMIT": 25,
    "LEARNLOOT_UDEMY_DISCOVERY_RENDER_WAIT_MS": 4500,
}


@pytest.fixture
def provider(db):
    return Provider.objects.create(name="Udemy", slug="udemy")


def test_registered_udemy_target_uses_runtime_settings(provider):
    with override_settings(**READY_SETTINGS):
        target = build_discovery_target(provider)

    assert isinstance(target.connector, UdemyFreeCourseProvider)
    assert target.source == "https://www.udemy.com/courses/free/"
    assert target.config.max_pages == 3
    assert target.config.item_limit == 25
    assert target.config.render_wait_ms == 4500
    assert target.connector.config.access_approved is True


def test_discovery_readiness_requires_explicit_access_acknowledgement(provider):
    settings = READY_SETTINGS | {
        "LEARNLOOT_UDEMY_DISCOVERY_ACCESS_APPROVED": False,
    }
    with override_settings(**settings):
        ready, reason = get_discovery_readiness(provider)

    assert ready is False
    assert "acknowledged" in reason


def test_discovery_source_display_redacts_accidental_url_credentials():
    displayed = safe_source_for_display(
        "https://user:secret@www.udemy.com/courses/free/?p=1"
    )

    assert displayed == "https://www.udemy.com/courses/free/?p=1"
    assert "user" not in displayed
    assert "secret" not in displayed


def test_unknown_provider_has_no_registered_discovery_connector(db):
    provider = Provider.objects.create(name="Other", slug="other")

    with pytest.raises(UnsupportedDiscoveryProvider):
        build_discovery_target(provider)


@pytest.mark.django_db
def test_celery_task_invokes_existing_discovery_pipeline(provider):
    fake_run = SimpleNamespace(
        pk=91,
        status=DiscoveryRun.Status.SUCCEEDED,
        records_found=5,
        records_new=3,
        records_updated=1,
        records_failed=1,
    )
    target = SimpleNamespace(connector=object(), source="source-a")

    with patch("discovery.tasks.build_discovery_target", return_value=target), patch(
        "discovery.tasks.execute_discovery", return_value=fake_run
    ) as execute, patch(
        "discovery.tasks.evaluate_provider_publication_candidates.delay"
    ) as publication_delay:
        result = run_provider_discovery.run(provider.pk)

    execute.assert_called_once_with(provider, target.connector, "source-a")
    publication_delay.assert_called_once_with(provider.pk)
    assert result == {
        "provider_id": provider.pk,
        "run_id": 91,
        "status": DiscoveryRun.Status.SUCCEEDED,
        "records_found": 5,
        "records_new": 3,
        "records_updated": 1,
        "records_failed": 1,
    }


@pytest.mark.django_db
def test_celery_task_skips_inactive_provider_before_building_connector(provider):
    provider.status = Provider.Status.INACTIVE
    provider.save(update_fields=("status",))

    with patch("discovery.tasks.build_discovery_target") as build, patch(
        "discovery.tasks.execute_discovery"
    ) as execute:
        result = run_provider_discovery.run(provider.pk)

    build.assert_not_called()
    execute.assert_not_called()
    assert result["status"] == "skipped"
    assert result["run_id"] == 0


@pytest.mark.django_db
def test_provider_admin_queue_action_enqueues_without_running_scraper(provider):
    model_admin = ProviderAdmin(Provider, admin.site)
    request = RequestFactory().post("/admin/providers/provider/")

    with override_settings(**READY_SETTINGS), patch.object(
        model_admin, "message_user"
    ), patch("providers.admin.run_provider_discovery.delay") as delay:
        model_admin.queue_discovery(
            request,
            Provider.objects.filter(pk=provider.pk),
        )

    delay.assert_called_once_with(provider.pk)
    assert DiscoveryRun.objects.count() == 0


@pytest.mark.django_db
def test_provider_admin_skips_inactive_provider(provider):
    provider.status = Provider.Status.INACTIVE
    provider.save(update_fields=("status",))
    model_admin = ProviderAdmin(Provider, admin.site)
    request = RequestFactory().post("/admin/providers/provider/")

    with override_settings(**READY_SETTINGS), patch.object(
        model_admin, "message_user"
    ), patch("providers.admin.run_provider_discovery.delay") as delay:
        model_admin.queue_discovery(
            request,
            Provider.objects.filter(pk=provider.pk),
        )

    delay.assert_not_called()


@pytest.mark.django_db
def test_provider_admin_skips_unacknowledged_access(provider):
    settings = READY_SETTINGS | {
        "LEARNLOOT_UDEMY_DISCOVERY_ACCESS_APPROVED": False,
    }
    model_admin = ProviderAdmin(Provider, admin.site)
    request = RequestFactory().post("/admin/providers/provider/")

    with override_settings(**settings), patch.object(
        model_admin, "message_user"
    ), patch("providers.admin.run_provider_discovery.delay") as delay:
        model_admin.queue_discovery(
            request,
            Provider.objects.filter(pk=provider.pk),
        )

    delay.assert_not_called()


@pytest.mark.django_db
def test_course_admin_visibility_actions_do_not_change_identity(provider):
    course = Course.objects.create(
        provider=provider,
        external_id="slug:sample",
        title="Sample",
        slug="sample",
        canonical_url="https://www.udemy.com/course/sample/",
    )
    model_admin = CourseAdmin(Course, admin.site)
    request = RequestFactory().post("/admin/courses/course/")

    with patch.object(model_admin, "message_user"):
        model_admin.hide_selected(request, Course.objects.filter(pk=course.pk))
        course.refresh_from_db()
        assert course.status == Course.Status.HIDDEN
        assert course.external_id == "slug:sample"
        assert course.slug == "sample"

        model_admin.archive_selected(request, Course.objects.filter(pk=course.pk))
        course.refresh_from_db()
        assert course.status == Course.Status.ARCHIVED
        assert course.external_id == "slug:sample"

        model_admin.activate_selected(request, Course.objects.filter(pk=course.pk))
        course.refresh_from_db()
        assert course.status == Course.Status.ACTIVE


def test_course_admin_exposes_audit_history_inlines():
    model_admin = CourseAdmin(Course, admin.site)

    assert model_admin.inlines == (
        CoursePriceInline,
        CourseSourceInline,
        CourseObservationInline,
        DealEligibilityInline,
        PublicationQueueInline,
    )
    assert model_admin.has_add_permission(RequestFactory().get("/")) is False
    assert model_admin.has_delete_permission(RequestFactory().get("/")) is False


def test_discovery_run_admin_is_read_only_audit_history():
    model_admin = DiscoveryRunAdmin(DiscoveryRun, admin.site)
    request = RequestFactory().get("/")

    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_delete_permission(request) is False
    assert "error_message" in model_admin.readonly_fields
    assert "records_failed" in model_admin.readonly_fields


def test_provider_queue_action_requires_change_permission_metadata():
    assert ProviderAdmin.queue_discovery.allowed_permissions == ["change"]