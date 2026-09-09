from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db.models import F, Prefetch, Q, QuerySet
from django.http import Http404, HttpRequest, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from pricing.models import CoursePrice
from providers.models import Provider
from tracking.services import OutboundDestinationError, resolve_outbound_destination

from .models import Course

DEFAULT_LIMIT = 24
MAX_LIMIT = 100
SITEMAP_MAX_COURSES = 5000


def _limit_from_request(request: HttpRequest) -> int:
    raw = request.GET.get("limit", str(DEFAULT_LIMIT))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(1, min(value, MAX_LIMIT))


def _freshness_cutoff():
    max_age_hours = max(
        int(getattr(settings, "LEARNLOOT_PUBLICATION_MAX_COURSE_AGE_HOURS", 24)),
        1,
    )
    return timezone.now() - timedelta(hours=max_age_hours)


def _base_course_queryset() -> QuerySet[Course]:
    latest_prices = CoursePrice.objects.order_by("-observed_at", "-id")
    return (
        Course.objects.filter(
            status=Course.Status.ACTIVE,
            provider__status=Provider.Status.ACTIVE,
            publication_eligibility__eligible=True,
            last_checked_at__gte=_freshness_cutoff(),
            publication_eligibility__evaluated_at__gte=F("last_checked_at"),
        )
        .select_related("provider", "publication_eligibility")
        .prefetch_related(Prefetch("prices", queryset=latest_prices, to_attr="public_prices"))
        .order_by("-publication_eligibility__score", "-last_checked_at", "title", "id")
    )


def _latest_price(course: Course) -> CoursePrice | None:
    prices = getattr(course, "public_prices", None)
    if prices is not None:
        return prices[0] if prices else None
    return course.prices.order_by("-observed_at", "-id").first()


def _is_latest_price_free(price: CoursePrice | None) -> bool:
    if price is None or not price.is_free:
        return False
    return price.amount in (None, Decimal("0"), Decimal("0.00"))


def _public_course_url(course: Course) -> str:
    base_url = str(getattr(settings, "LEARNLOOT_PUBLIC_BASE_URL", "")).rstrip("/")
    path = f"/courses/{course.provider.slug}/{course.slug}"
    return f"{base_url}{path}" if base_url else path


def _outbound_url(request: HttpRequest, course: Course) -> str:
    path = reverse(
        "tracking:outbound-redirect",
        kwargs={"provider_slug": course.provider.slug, "course_slug": course.slug},
    )
    return request.build_absolute_uri(path)


def _file_url(request: HttpRequest, field) -> str:
    if not field:
        return ""
    try:
        return request.build_absolute_uri(field.url)
    except (ValueError, AttributeError):
        return ""


def _course_thumbnail_url(request: HttpRequest, course: Course) -> str:
    return _file_url(request, course.editorial_image) or course.thumbnail_url


def _course_social_image_url(request: HttpRequest, course: Course) -> str:
    return (
        _file_url(request, course.social_image)
        or _file_url(request, course.editorial_image)
        or course.thumbnail_url
    )


def _price_payload(price: CoursePrice | None) -> dict[str, Any] | None:
    if price is None:
        return None
    return {
        "amount": str(price.amount) if price.amount is not None else None,
        "currency": price.currency,
        "is_free": price.is_free,
        "price_type": price.price_type,
        "observed_at": price.observed_at.isoformat(),
    }


def _course_summary(request: HttpRequest, course: Course) -> dict[str, Any]:
    price = _latest_price(course)
    eligibility = course.publication_eligibility
    return {
        "id": course.id,
        "provider": {"slug": course.provider.slug, "name": course.provider.name},
        "title": course.public_title,
        "slug": course.slug,
        "url": _public_course_url(course),
        "outbound_url": _outbound_url(request, course),
        "thumbnail_url": _course_thumbnail_url(request, course),
        "instructor_name": course.instructor_name,
        "rating": str(course.rating) if course.rating is not None else None,
        "review_count": course.review_count,
        "student_count": course.student_count,
        "duration_minutes": course.duration_minutes,
        "score": eligibility.score,
        "last_checked_at": course.last_checked_at.isoformat() if course.last_checked_at else None,
        "latest_price": _price_payload(price),
    }


def _course_detail(request: HttpRequest, course: Course) -> dict[str, Any]:
    payload = _course_summary(request, course)
    payload.update(
        {
            "description": course.public_description,
            "description_html": course.public_description_html,
            "first_seen_at": course.first_seen_at.isoformat(),
            "last_seen_at": course.last_seen_at.isoformat(),
            "eligibility": {
                "score": course.publication_eligibility.score,
                "evaluated_at": course.publication_eligibility.evaluated_at.isoformat(),
            },
            "seo": {
                "title": course.public_seo_title,
                "description": course.public_meta_description,
                "keywords": course.meta_keywords,
                "social_image_url": _course_social_image_url(request, course),
            },
        }
    )
    return payload


def _visible_course(course: Course) -> bool:
    if not _is_latest_price_free(_latest_price(course)):
        return False
    try:
        resolve_outbound_destination(course)
    except OutboundDestinationError:
        return False
    return True


def _visible_public_courses(request: HttpRequest) -> list[Course]:
    queryset = _base_course_queryset()
    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(editorial_title__icontains=query)
            | Q(instructor_name__icontains=query)
            | Q(description__icontains=query)
            | Q(editorial_description__icontains=query)
            | Q(meta_keywords__icontains=query)
        )

    courses: list[Course] = []
    for course in queryset[: MAX_LIMIT * 3]:
        if not _visible_course(course):
            continue
        courses.append(course)
        if len(courses) >= _limit_from_request(request):
            break
    return courses


def get_public_course_or_404(provider_slug: str, course_slug: str) -> Course:
    try:
        course = _base_course_queryset().get(provider__slug=provider_slug, slug=course_slug)
    except Course.DoesNotExist as exc:
        raise Http404("Course is not public") from exc
    if not _visible_course(course):
        raise Http404("Course is not public")
    return course


@require_GET
def public_course_list(request: HttpRequest) -> JsonResponse:
    courses = _visible_public_courses(request)
    return JsonResponse(
        {
            "generated_at": timezone.now().isoformat(),
            "count": len(courses),
            "results": [_course_summary(request, course) for course in courses],
        }
    )


@require_GET
def public_course_sitemap(request: HttpRequest) -> JsonResponse:
    entries: list[dict[str, str]] = []
    for course in _base_course_queryset()[:SITEMAP_MAX_COURSES]:
        if not _visible_course(course):
            continue
        entries.append({"url": _public_course_url(course), "last_modified": course.updated_at.isoformat()})
    return JsonResponse({"results": entries})


@require_GET
def public_course_detail(request: HttpRequest, provider_slug: str, course_slug: str) -> JsonResponse:
    course = get_public_course_or_404(provider_slug, course_slug)
    return JsonResponse(_course_detail(request, course))
