import json
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings

from courses.models import Course
from discovery.models import DiscoveryObservation, DiscoveryRun
from discovery.udemy_catalog import UDEMY_DEFAULT_SEARCH_URL
from providers.models import Provider


@pytest.fixture
def staff_client(db):
    user = get_user_model().objects.create_user(
        username="discovery-admin",
        password="secret-pass",
        is_staff=True,
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def provider(db):
    return Provider.objects.create(
        name="Udemy",
        slug="udemy",
        status=Provider.Status.ACTIVE,
    )


@pytest.mark.django_db
@override_settings(LEARNLOOT_UDEMY_DISCOVERY_ACCESS_APPROVED=True)
def test_admin_can_queue_requested_free_courses_without_running_scraper(staff_client, provider):
    with patch("cms.api.ensure_local_discovery_worker", return_value="started"), patch(
        "discovery.tasks.run_provider_discovery.delay",
        return_value=SimpleNamespace(id="task-123"),
    ) as delay:
        response = staff_client.post(
            "/api/admin/discovery/runs/queue/",
            data=json.dumps({"course_count": 75}),
            content_type="application/json",
        )

    assert response.status_code == 202
    assert response.json()["task_id"] == "task-123"
    assert response.json()["worker_started"] is True
    assert response.json()["course_count"] == 75
    assert response.json()["source_url"] == UDEMY_DEFAULT_SEARCH_URL
    assert response.json()["search_filters"]["label"] == "SQL courses · English · Free"
    delay.assert_called_once_with(provider.pk, UDEMY_DEFAULT_SEARCH_URL, 75)
    assert DiscoveryRun.objects.count() == 0


@pytest.mark.django_db
@override_settings(LEARNLOOT_UDEMY_DISCOVERY_ACCESS_APPROVED=True)
def test_admin_rejects_an_invalid_course_count(staff_client, provider):
    with patch("cms.api.ensure_local_discovery_worker") as ensure_worker, patch(
        "discovery.tasks.run_provider_discovery.delay"
    ) as delay:
        response = staff_client.post(
            "/api/admin/discovery/runs/queue/",
            data=json.dumps({"course_count": 0}),
            content_type="application/json",
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Number of courses must be between 1 and 5000."
    ensure_worker.assert_not_called()
    delay.assert_not_called()


@pytest.mark.django_db
@override_settings(LEARNLOOT_UDEMY_DISCOVERY_ACCESS_APPROVED=True)
def test_admin_does_not_queue_overlapping_discovery(staff_client, provider):
    DiscoveryRun.objects.create(
        provider=provider,
        source=UDEMY_DEFAULT_SEARCH_URL,
    )

    with patch("cms.api.ensure_local_discovery_worker", return_value="available"), patch(
        "discovery.tasks.run_provider_discovery.delay"
    ) as delay:
        response = staff_client.post(
            "/api/admin/discovery/runs/queue/",
            data=json.dumps({"course_count": 100}),
            content_type="application/json",
        )

    assert response.status_code == 409
    assert "already in progress" in response.json()["detail"]
    delay.assert_not_called()


@pytest.mark.django_db
@override_settings(
    DEBUG=True,
    LEARNLOOT_ADMIN_AUTO_START_CELERY_WORKER=True,
)
def test_local_worker_start_uses_fixed_command_without_a_shell(tmp_path, settings):
    from discovery.worker import ensure_local_discovery_worker

    settings.BASE_DIR = tmp_path
    with patch("discovery.worker._worker_nodes", return_value=set()), patch(
        "discovery.worker.cache.add", return_value=True
    ), patch("discovery.worker.subprocess.Popen") as popen:
        status = ensure_local_discovery_worker()

    command, options = popen.call_args
    assert status == "started"
    assert command[0][0:6] == [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "config",
        "worker",
    ]
    assert any(argument.startswith("--hostname=learnloot-discovery-") for argument in command[0])
    assert "shell" not in options


@pytest.mark.django_db
@override_settings(
    DEBUG=True,
    LEARNLOOT_ADMIN_AUTO_START_CELERY_WORKER=True,
)
def test_local_worker_replaces_an_idle_stale_revision(tmp_path, settings):
    from discovery.worker import ensure_local_discovery_worker

    settings.BASE_DIR = tmp_path
    with patch("discovery.worker.socket.gethostname", return_value="test-host"), patch(
        "discovery.worker._worker_nodes",
        return_value={"celery@test-host"},
    ), patch("discovery.worker._stop_stale_local_workers") as stop, patch(
        "discovery.worker.cache.add", return_value=True
    ), patch("discovery.worker.subprocess.Popen"):
        status = ensure_local_discovery_worker()

    assert status == "started"
    stop.assert_called_once_with({"celery@test-host"})


@pytest.mark.django_db
def test_admin_lists_discovery_runs_and_observations(staff_client, provider):
    course = Course.objects.create(
        provider=provider,
        external_id="course-123",
        title="Scraped title",
        editorial_title="Edited title",
        slug="course-123",
        canonical_url="https://www.udemy.com/course/course-123/",
    )
    run = DiscoveryRun.objects.create(
        provider=provider,
        source="https://user:secret@www.udemy.com/courses/free/",
        status=DiscoveryRun.Status.SUCCEEDED,
        records_found=2,
        records_new=1,
        records_failed=1,
    )
    DiscoveryObservation.objects.create(
        run=run,
        course=course,
        external_id=course.external_id,
        source_url=course.canonical_url,
    )
    DiscoveryObservation.objects.create(
        run=run,
        external_id="rejected-456",
        source_url="https://www.udemy.com/course/rejected-456/",
    )

    listing = staff_client.get("/api/admin/discovery/runs/")
    detail = staff_client.get(f"/api/admin/discovery/runs/{run.pk}/")

    assert listing.status_code == 200
    assert listing.json()["filters"]["default_course_count"] == 100
    assert listing.json()["results"][0]["id"] == run.pk
    assert listing.json()["results"][0]["source"] == "https://www.udemy.com/courses/free/"
    assert listing.json()["results"][0]["search_filters"]["label"] == "Legacy free catalog"
    assert detail.status_code == 200
    assert detail.json()["observations"]["count"] == 2
    assert detail.json()["observations"]["results"][0]["course"] == {
        "id": course.pk,
        "title": "Edited title",
    }
    assert detail.json()["observations"]["results"][1]["course"] is None
