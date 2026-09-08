from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.test import Client, override_settings
from django.utils import timezone

from courses.models import Course
from pricing.models import CoursePrice
from providers.models import Provider
from publishing.models import DealEligibility


@pytest.fixture
def provider(db):
    return Provider.objects.create(
        name="Udemy",
        slug="udemy",
        status=Provider.Status.ACTIVE,
    )


def make_course(
    provider,
    *,
    title="Python Fast Track",
    slug="python-fast-track",
    external_id="course-1",
    course_status=Course.Status.ACTIVE,
    provider_status=Provider.Status.ACTIVE,
    eligible=True,
    is_free=True,
    amount=Decimal("0.00"),
    rating=Decimal("4.60"),
    review_count=1200,
    checked_at=None,
    evaluated_at=None,
):
    provider.status = provider_status
    provider.save(update_fields=["status"])
    now = timezone.now()
    checked_at = checked_at or now
    evaluated_at = evaluated_at or checked_at
    course = Course.objects.create(
        provider=provider,
        external_id=external_id,
        title=title,
        slug=slug,
        canonical_url=f"https://example.com/course/{slug}/",
        thumbnail_url="https://example.com/thumb.jpg",
        instructor_name="Jane Instructor",
        rating=rating,
        review_count=review_count,
        student_count=25000,
        duration_minutes=180,
        description="A practical public course for LearnLoot visitors.",
        status=course_status,
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
        score=92,
        eligible=eligible,
        reasons=[],
        evaluated_at=evaluated_at,
    )
    return course


@pytest.mark.django_db
@override_settings(LEARNLOOT_PUBLIC_BASE_URL="https://learnloot.test")
def test_public_course_list_exposes_only_active_eligible_free_courses(provider):
    public_course = make_course(provider)
    make_course(
        provider,
        external_id="paid",
        slug="paid-course",
        is_free=False,
        amount=Decimal("19.99"),
    )
    make_course(
        provider,
        external_id="hidden",
        slug="hidden-course",
        course_status=Course.Status.HIDDEN,
    )
    make_course(
        provider,
        external_id="ineligible",
        slug="ineligible-course",
        eligible=False,
    )

    response = Client().get("/api/public/courses/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    result = payload["results"][0]
    assert result["id"] == public_course.id
    assert result["title"] == "Python Fast Track"
    assert result["url"] == "https://learnloot.test/courses/udemy/python-fast-track"
    assert result["provider_url"] == "https://example.com/course/python-fast-track/"
    assert result["latest_price"]["is_free"] is True
    assert result["score"] == 92


@pytest.mark.django_db
@override_settings(LEARNLOOT_PUBLIC_BASE_URL="https://learnloot.test")
def test_public_course_detail_returns_seo_landing_page_payload(provider):
    course = make_course(provider)

    response = Client().get(
        f"/api/public/courses/{provider.slug}/{course.slug}/"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == course.title
    assert payload["description"] == course.description
    assert payload["provider"]["slug"] == "udemy"
    assert payload["eligibility"]["score"] == 92
    assert payload["url"] == "https://learnloot.test/courses/udemy/python-fast-track"


@pytest.mark.django_db
def test_public_course_detail_404s_when_latest_price_is_no_longer_free(provider):
    course = make_course(provider)
    CoursePrice.objects.create(
        course=course,
        amount=Decimal("12.99"),
        currency="USD",
        is_free=False,
        price_type="paid",
        observed_at=timezone.now(),
        source_url=course.canonical_url,
    )

    response = Client().get(
        f"/api/public/courses/{provider.slug}/{course.slug}/"
    )

    assert response.status_code == 404


@pytest.mark.django_db
@override_settings(LEARNLOOT_PUBLICATION_MAX_COURSE_AGE_HOURS=24)
def test_public_api_hides_stale_courses(provider):
    stale_time = timezone.now() - timedelta(hours=25)
    course = make_course(
        provider,
        checked_at=stale_time,
        evaluated_at=stale_time,
    )

    assert Client().get("/api/public/courses/").json()["results"] == []
    detail = Client().get(
        f"/api/public/courses/{provider.slug}/{course.slug}/"
    )
    assert detail.status_code == 404


@pytest.mark.django_db
def test_public_api_hides_course_until_latest_check_is_re_evaluated(provider):
    evaluated_at = timezone.now() - timedelta(minutes=5)
    checked_at = timezone.now()
    make_course(
        provider,
        checked_at=checked_at,
        evaluated_at=evaluated_at,
    )

    response = Client().get("/api/public/courses/")

    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_public_course_list_supports_search_and_limit(provider):
    make_course(provider, external_id="python", slug="python", title="Python Basics")
    make_course(provider, external_id="django", slug="django", title="Django Basics")
    make_course(provider, external_id="react", slug="react", title="React Basics")

    response = Client().get("/api/public/courses/?q=django&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["title"] == "Django Basics"


@pytest.mark.django_db
def test_public_api_does_not_expose_inactive_provider_courses(provider):
    make_course(provider, provider_status=Provider.Status.INACTIVE)

    response = Client().get("/api/public/courses/")

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_phase8_frontend_routes_are_implemented():
    root = Path(__file__).resolve().parents[2]

    homepage = root / "frontend" / "src" / "app" / "page.tsx"
    catalog = root / "frontend" / "src" / "app" / "courses" / "page.tsx"
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
    frontend_env = root / "frontend" / ".env.example"

    for path in (homepage, catalog, detail, api, frontend_env):
        assert path.exists(), path

    homepage_text = homepage.read_text(encoding="utf-8")
    assert "getCourses({ limit: 6 })" in homepage_text
    assert "NEXT_PUBLIC_TELEGRAM_CHANNEL_URL" in homepage_text
    assert "System status" not in homepage_text

    assert "Search" in catalog.read_text(encoding="utf-8")
    detail_text = detail.read_text(encoding="utf-8")
    assert "generateMetadata" in detail_text
    assert "Continue to free course" in detail_text
    assert 'rel="noopener noreferrer"' in detail_text
    assert "/public/courses/" in api.read_text(encoding="utf-8")
