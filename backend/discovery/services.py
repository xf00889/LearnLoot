from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from courses.models import Course, CourseSource
from pricing.models import CoursePrice
from providers.models import Provider

from .contracts import DiscoveryIdentity, NormalizedCourse
from .models import DiscoveryObservation, DiscoveryRun
from .providers.base import CourseProvider
from .validators import CourseValidationError, validate_course


class DiscoveryExecutionError(RuntimeError):
    def __init__(self, run_id: int, message: str):
        self.run_id = run_id
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CourseUpsertResult:
    course: Course
    created: bool
    materially_changed: bool
    price_created: bool


def _build_unique_slug(provider: Provider, title: str, external_id: str) -> str:
    base = slugify(title) or "course"
    base = base[:600]

    if not Course.objects.filter(provider=provider, slug=base).exists():
        return base

    suffix_seed = slugify(external_id) or "item"
    suffix = f"-{suffix_seed[:80]}"
    candidate = f"{base[: 600 - len(suffix)]}{suffix}"
    counter = 2

    while Course.objects.filter(provider=provider, slug=candidate).exists():
        counter_suffix = f"-{counter}"
        candidate = f"{base[: 600 - len(suffix) - len(counter_suffix)]}{suffix}{counter_suffix}"
        counter += 1

    return candidate


def _same_price_state(price: CoursePrice, course: NormalizedCourse) -> bool:
    amount = price.amount
    if amount is not None:
        amount = Decimal(amount)

    return (
        amount == course.price_amount
        and price.currency == course.currency
        and price.is_free == course.is_free
        and price.price_type == course.price_type
    )


def _record_price_if_changed(
    course_model: Course,
    course: NormalizedCourse,
    observed_at,
) -> bool:
    latest = course_model.prices.order_by("-observed_at", "-id").first()
    if latest is not None and _same_price_state(latest, course):
        return False

    CoursePrice.objects.create(
        course=course_model,
        amount=course.price_amount,
        currency=course.currency,
        is_free=course.is_free,
        price_type=course.price_type,
        observed_at=observed_at,
        source_url=course.source_url,
    )
    return True


def _touch_source(course_model: Course, course: NormalizedCourse, observed_at) -> None:
    existing = (
        CourseSource.objects.filter(
            course=course_model,
            source_url=course.source_url,
            source_type=course.source_type,
        )
        .order_by("id")
        .first()
    )

    if existing is None:
        CourseSource.objects.create(
            course=course_model,
            source_url=course.source_url,
            source_type=course.source_type,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
        )
        return

    existing.last_seen_at = observed_at
    existing.save(update_fields=("last_seen_at",))


def upsert_course(
    provider: Provider,
    course: NormalizedCourse,
    observed_at=None,
) -> CourseUpsertResult:
    validate_course(course)
    observed_at = observed_at or timezone.now()

    with transaction.atomic():
        course_model = (
            Course.objects.select_for_update()
            .filter(provider=provider, external_id=course.external_id)
            .first()
        )

        created = course_model is None
        materially_changed = False

        if course_model is None:
            course_model = Course.objects.create(
                provider=provider,
                external_id=course.external_id,
                title=course.title,
                slug=_build_unique_slug(provider, course.title, course.external_id),
                canonical_url=course.canonical_url,
                thumbnail_url=course.thumbnail_url,
                instructor_name=course.instructor_name,
                rating=course.rating,
                review_count=course.review_count,
                student_count=course.student_count,
                duration_minutes=course.duration_minutes,
                description=course.description,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                last_checked_at=observed_at,
            )
        else:
            mutable_fields = {
                "title": course.title,
                "canonical_url": course.canonical_url,
                "thumbnail_url": course.thumbnail_url,
                "instructor_name": course.instructor_name,
                "rating": course.rating,
                "review_count": course.review_count,
                "student_count": course.student_count,
                "duration_minutes": course.duration_minutes,
                "description": course.description,
            }
            changed_fields: list[str] = []
            for field_name, value in mutable_fields.items():
                if field_name == "thumbnail_url" and not str(value or "").strip():
                    # A transient card/detail-image miss must not erase the last
                    # successfully observed Udemy/provider image.
                    continue
                if getattr(course_model, field_name) != value:
                    setattr(course_model, field_name, value)
                    changed_fields.append(field_name)

            materially_changed = bool(changed_fields)
            course_model.last_seen_at = observed_at
            course_model.last_checked_at = observed_at
            course_model.updated_at = timezone.now()
            course_model.save(
                update_fields=(
                    *changed_fields,
                    "last_seen_at",
                    "last_checked_at",
                    "updated_at",
                )
            )

        _touch_source(course_model, course, observed_at)
        price_created = _record_price_if_changed(course_model, course, observed_at)

    return CourseUpsertResult(
        course=course_model,
        created=created,
        materially_changed=materially_changed or (not created and price_created),
        price_created=price_created,
    )


def _safe_identity(connector: CourseProvider, raw_course, source: str) -> DiscoveryIdentity:
    try:
        identity = connector.identify(raw_course, source)
    except (TypeError, ValueError, KeyError):
        return DiscoveryIdentity(external_id="", source_url=source)

    return DiscoveryIdentity(
        external_id=identity.external_id[:100],
        source_url=identity.source_url or source,
    )


def _finish_run(
    run: DiscoveryRun,
    *,
    status: str,
    records_found: int,
    records_new: int,
    records_updated: int,
    records_failed: int,
    error_message: str = "",
) -> DiscoveryRun:
    run.status = status
    run.finished_at = timezone.now()
    run.records_found = records_found
    run.records_new = records_new
    run.records_updated = records_updated
    run.records_failed = records_failed
    run.error_message = error_message
    run.save(
        update_fields=(
            "status",
            "finished_at",
            "records_found",
            "records_new",
            "records_updated",
            "records_failed",
            "error_message",
        )
    )
    return run


def execute_discovery(
    provider: Provider,
    connector: CourseProvider,
    source: str,
) -> DiscoveryRun:
    run = DiscoveryRun.objects.create(provider=provider, source=source)
    records_found = 0
    records_new = 0
    records_updated = 0
    records_failed = 0

    try:
        if provider.status != Provider.Status.ACTIVE:
            raise ValueError("provider is inactive")
        if connector.key != provider.slug:
            raise ValueError("connector key does not match provider slug")

        connector.validate_access()

        for raw_course in connector.discover(source):
            records_found += 1
            identity = _safe_identity(connector, raw_course, source)
            observed_at = timezone.now()

            try:
                normalized = connector.normalize(raw_course, source)
                validate_course(normalized)
                result = upsert_course(provider, normalized, observed_at)
            except (CourseValidationError, TypeError, ValueError, KeyError):
                records_failed += 1
                DiscoveryObservation.objects.create(
                    run=run,
                    external_id=identity.external_id,
                    source_url=identity.source_url,
                    observed_at=observed_at,
                )
                continue

            DiscoveryObservation.objects.create(
                run=run,
                course=result.course,
                external_id=normalized.external_id,
                source_url=normalized.source_url,
                observed_at=observed_at,
            )

            if result.created:
                records_new += 1
            elif result.materially_changed:
                records_updated += 1

    except Exception as exc:
        error_message = f"{type(exc).__name__} during provider discovery"
        _finish_run(
            run,
            status=DiscoveryRun.Status.FAILED,
            records_found=records_found,
            records_new=records_new,
            records_updated=records_updated,
            records_failed=records_failed,
            error_message=error_message,
        )
        raise DiscoveryExecutionError(run.pk, error_message) from exc

    return _finish_run(
        run,
        status=DiscoveryRun.Status.SUCCEEDED,
        records_found=records_found,
        records_new=records_new,
        records_updated=records_updated,
        records_failed=records_failed,
    )