import pytest
from django.db import IntegrityError, transaction

from courses.models import Course
from discovery.models import DiscoveryObservation, DiscoveryRun
from providers.models import Provider


@pytest.mark.django_db
def test_discovery_run_starts_with_zero_counts():
    provider = Provider.objects.create(name="Udemy", slug="udemy")

    run = DiscoveryRun.objects.create(
        provider=provider,
        source="development-free-listing",
    )

    assert run.status == DiscoveryRun.Status.RUNNING
    assert run.records_found == 0
    assert run.records_new == 0
    assert run.records_updated == 0
    assert run.records_failed == 0


@pytest.mark.django_db
def test_discovery_observation_can_be_linked_to_course():
    provider = Provider.objects.create(name="Udemy", slug="udemy")
    course = Course.objects.create(
        provider=provider,
        external_id="course-123",
        title="Python Course",
        slug="python-course",
        canonical_url="https://example.com/courses/course-123",
    )
    run = DiscoveryRun.objects.create(provider=provider)

    observation = DiscoveryObservation.objects.create(
        run=run,
        course=course,
        external_id=course.external_id,
        source_url="https://example.com/deals/python",
    )

    assert observation.course == course
    assert observation in run.observations.all()