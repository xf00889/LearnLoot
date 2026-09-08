import pytest
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from courses.models import Course, CourseSource
from providers.models import Provider


def make_provider(*, name="Udemy", slug="udemy"):
    return Provider.objects.create(name=name, slug=slug)


def make_course(provider, *, external_id="course-123", slug="python-course"):
    return Course.objects.create(
        provider=provider,
        external_id=external_id,
        title="Python Course",
        slug=slug,
        canonical_url="https://example.com/courses/course-123",
    )


@pytest.mark.django_db
def test_course_uses_provider_and_external_id_as_identity():
    provider = make_provider()
    make_course(provider)

    with pytest.raises(IntegrityError), transaction.atomic():
        make_course(provider, slug="different-slug")


@pytest.mark.django_db
def test_same_external_id_is_allowed_for_different_providers():
    first_provider = make_provider()
    second_provider = make_provider(name="Other Provider", slug="other-provider")

    first = make_course(first_provider)
    second = make_course(second_provider)

    assert first.external_id == second.external_id
    assert first.provider_id != second.provider_id


@pytest.mark.django_db
def test_course_slug_is_unique_within_provider():
    provider = make_provider()
    make_course(provider, external_id="course-1", slug="shared-slug")

    with pytest.raises(IntegrityError), transaction.atomic():
        make_course(provider, external_id="course-2", slug="shared-slug")


@pytest.mark.django_db
def test_provider_with_courses_is_protected_from_deletion():
    provider = make_provider()
    make_course(provider)

    with pytest.raises(ProtectedError):
        provider.delete()


@pytest.mark.django_db
def test_course_source_tracks_where_course_was_discovered():
    course = make_course(make_provider())

    source = CourseSource.objects.create(
        course=course,
        source_url="https://example.com/deals/python",
        source_type="listing",
    )

    assert source.course == course
    assert source in course.sources.all()