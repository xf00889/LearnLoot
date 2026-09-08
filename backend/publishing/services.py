from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from courses.models import Course
from pricing.models import CoursePrice
from providers.models import Provider

from .models import AdminOverride, DealEligibility, PublicationQueueItem


@dataclass(frozen=True, slots=True)
class PublicationRules:
    min_rating: Decimal
    min_reviews: int
    min_score: int
    max_course_age: timedelta
    cooldown: timedelta


@dataclass(frozen=True, slots=True)
class CourseEvaluationResult:
    course_id: int
    eligible: bool
    score: int
    reasons: tuple[str, ...]
    override_applied: bool
    queue_item_id: int | None
    queue_created: bool


@dataclass(frozen=True, slots=True)
class ProviderEvaluationResult:
    provider_id: int
    courses_evaluated: int
    eligible: int
    ineligible: int
    queued: int


def get_publication_rules() -> PublicationRules:
    return PublicationRules(
        min_rating=Decimal(str(settings.LEARNLOOT_PUBLICATION_MIN_RATING)),
        min_reviews=settings.LEARNLOOT_PUBLICATION_MIN_REVIEWS,
        min_score=settings.LEARNLOOT_PUBLICATION_MIN_SCORE,
        max_course_age=timedelta(
            hours=settings.LEARNLOOT_PUBLICATION_MAX_COURSE_AGE_HOURS
        ),
        cooldown=timedelta(hours=settings.LEARNLOOT_PUBLICATION_COOLDOWN_HOURS),
    )


def _latest_price(course: Course) -> CoursePrice | None:
    return course.prices.order_by("-observed_at", "-pk").first()


def _review_points(review_count: int | None) -> int:
    if review_count is None or review_count <= 0:
        return 0
    if review_count >= 10_000:
        return 20
    if review_count >= 1_000:
        return 18
    if review_count >= 100:
        return 14
    if review_count >= 25:
        return 8
    return 4


def _rating_points(rating: Decimal | None) -> int:
    if rating is None:
        return 0

    bounded = min(max(Decimal(rating), Decimal("0")), Decimal("5"))
    points = (bounded / Decimal("5") * Decimal("30")).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )
    return int(points)


def calculate_deal_score(course: Course, latest_price: CoursePrice | None) -> int:
    score = 0

    if (
        latest_price is not None
        and latest_price.is_free
        and (latest_price.amount is None or Decimal(latest_price.amount) == Decimal("0"))
    ):
        score += 40

    score += _rating_points(course.rating)
    score += _review_points(course.review_count)

    completeness_checks = (
        bool(course.thumbnail_url),
        bool(course.instructor_name),
        course.duration_minutes is not None and course.duration_minutes > 0,
        bool(course.description),
        course.student_count is not None and course.student_count > 0,
    )
    score += sum(2 for present in completeness_checks if present)

    return min(score, 100)


def _get_override(course: Course) -> AdminOverride | None:
    try:
        return course.publication_override
    except AdminOverride.DoesNotExist:
        return None


def _latest_sent_at(course: Course):
    return (
        course.publication_queue_items.filter(
            status=PublicationQueueItem.Status.SENT,
            sent_at__isnull=False,
        )
        .order_by("-sent_at", "-pk")
        .values_list("sent_at", flat=True)
        .first()
    )


def _absolute_reasons(
    course: Course,
    latest_price: CoursePrice | None,
    rules: PublicationRules,
    now,
) -> list[str]:
    reasons: list[str] = []

    if course.provider.status != Provider.Status.ACTIVE:
        reasons.append("provider_inactive")
    if course.status != Course.Status.ACTIVE:
        reasons.append("course_not_active")
    if latest_price is None:
        reasons.append("no_price_observation")
    else:
        if not latest_price.is_free:
            reasons.append("price_not_free")
        if latest_price.is_free and latest_price.amount is not None:
            if Decimal(latest_price.amount) != Decimal("0"):
                reasons.append("free_price_conflict")

    # Price observations are intentionally change-only history. Use the course
    # last_checked timestamp to decide freshness so a stable free price does not
    # become stale merely because no new price row was inserted.
    if course.last_checked_at is None:
        reasons.append("course_never_checked")
    elif now - course.last_checked_at > rules.max_course_age:
        reasons.append("course_check_stale")

    return reasons


def _quality_reasons(
    course: Course,
    score: int,
    rules: PublicationRules,
) -> list[str]:
    reasons: list[str] = []

    if course.rating is None:
        reasons.append("rating_missing")
    elif Decimal(course.rating) < rules.min_rating:
        reasons.append("rating_below_minimum")

    if course.review_count is None:
        reasons.append("review_count_missing")
    elif course.review_count < rules.min_reviews:
        reasons.append("review_count_below_minimum")

    if score < rules.min_score:
        reasons.append("score_below_minimum")

    return reasons


def _cooldown_reasons(
    course: Course,
    rules: PublicationRules,
    now,
) -> list[str]:
    latest_sent_at = _latest_sent_at(course)
    if latest_sent_at is None:
        return []

    if now - latest_sent_at < rules.cooldown:
        return ["publication_cooldown"]
    return []


def _cancel_queued_items(course: Course, reasons: list[str], now) -> None:
    if not reasons:
        message = "Eligibility changed"
    else:
        message = "Eligibility changed: " + ", ".join(reasons)

    course.publication_queue_items.filter(
        status=PublicationQueueItem.Status.QUEUED
    ).update(
        status=PublicationQueueItem.Status.CANCELLED,
        error_message=message,
        updated_at=now,
    )


def evaluate_course_for_publication(
    course: Course,
    *,
    rules: PublicationRules | None = None,
    now=None,
    create_queue_item: bool = True,
) -> CourseEvaluationResult:
    rules = rules or get_publication_rules()
    now = now or timezone.now()

    # The provider is a hard publication gate, so refresh/select it even when a
    # caller supplied a Course instance from a lightweight queryset.
    course = Course.objects.select_related("provider").get(pk=course.pk)
    latest_price = _latest_price(course)
    score = calculate_deal_score(course, latest_price)
    override = _get_override(course)

    absolute_reasons = _absolute_reasons(course, latest_price, rules, now)
    quality_reasons = _quality_reasons(course, score, rules)
    cooldown_reasons = _cooldown_reasons(course, rules, now)

    override_applied = False
    reasons: list[str]
    eligible: bool

    if absolute_reasons:
        reasons = absolute_reasons
        eligible = False
    elif override is not None and override.decision == AdminOverride.Decision.FORCE_INELIGIBLE:
        reasons = ["admin_force_ineligible"]
        override_applied = True
        eligible = False
    elif override is not None and override.decision == AdminOverride.Decision.FORCE_ELIGIBLE:
        reasons = ["admin_force_eligible"]
        override_applied = True
        eligible = True
    else:
        reasons = [*quality_reasons, *cooldown_reasons]
        eligible = not reasons

    with transaction.atomic():
        eligibility, _created = DealEligibility.objects.update_or_create(
            course=course,
            defaults={
                "latest_price": latest_price,
                "score": score,
                "eligible": eligible,
                "override_applied": override_applied,
                "reasons": reasons,
                "evaluated_at": now,
            },
        )

        if not eligible:
            _cancel_queued_items(course, reasons, now)
            return CourseEvaluationResult(
                course_id=course.pk,
                eligible=False,
                score=score,
                reasons=tuple(reasons),
                override_applied=override_applied,
                queue_item_id=None,
                queue_created=False,
            )

        existing = course.publication_queue_items.filter(
            status=PublicationQueueItem.Status.QUEUED
        ).first()
        if existing is not None or not create_queue_item:
            return CourseEvaluationResult(
                course_id=course.pk,
                eligible=True,
                score=score,
                reasons=tuple(reasons),
                override_applied=override_applied,
                queue_item_id=existing.pk if existing is not None else None,
                queue_created=False,
            )

        # A Telegram delivery that ended in a known failure or an ambiguous
        # network outcome requires explicit operator handling. Do not create a
        # fresh queue item on the next discovery/evaluation cycle, because that
        # could bypass the audited retry decision and duplicate a Telegram post.
        unresolved_delivery = (
            course.publication_queue_items.filter(
                status=PublicationQueueItem.Status.FAILED,
                telegram_post__status__in=("failed", "ambiguous"),
            )
            .order_by("-queued_at", "-pk")
            .first()
        )
        if unresolved_delivery is not None:
            return CourseEvaluationResult(
                course_id=course.pk,
                eligible=True,
                score=score,
                reasons=tuple(reasons),
                override_applied=override_applied,
                queue_item_id=unresolved_delivery.pk,
                queue_created=False,
            )

        try:
            # Use a nested savepoint so a concurrent unique-constraint race can
            # be recovered without marking the surrounding eligibility
            # transaction as broken.
            with transaction.atomic():
                queue_item = PublicationQueueItem.objects.create(
                    course=course,
                    latest_price=latest_price,
                    score=score,
                    override_applied=override_applied,
                    reasons=reasons,
                    status=PublicationQueueItem.Status.QUEUED,
                    queued_at=now,
                )
            queue_created = True
        except IntegrityError:
            # The conditional unique constraint is the final race-condition
            # guard if two workers evaluate the same course concurrently.
            queue_item = course.publication_queue_items.get(
                status=PublicationQueueItem.Status.QUEUED
            )
            queue_created = False

        # Keep the snapshot variable intentionally referenced so future queue
        # consumers can rely on the eligibility row having been committed in
        # the same transaction as the queue decision.
        _ = eligibility

    return CourseEvaluationResult(
        course_id=course.pk,
        eligible=True,
        score=score,
        reasons=tuple(reasons),
        override_applied=override_applied,
        queue_item_id=queue_item.pk,
        queue_created=queue_created,
    )


def evaluate_provider_courses(
    provider: Provider,
    *,
    rules: PublicationRules | None = None,
    now=None,
) -> ProviderEvaluationResult:
    rules = rules or get_publication_rules()
    now = now or timezone.now()

    evaluated = 0
    eligible = 0
    queued = 0

    for course in provider.courses.order_by("pk").iterator():
        result = evaluate_course_for_publication(
            course,
            rules=rules,
            now=now,
            create_queue_item=True,
        )
        evaluated += 1
        if result.eligible:
            eligible += 1
        if result.queue_created:
            queued += 1

    return ProviderEvaluationResult(
        provider_id=provider.pk,
        courses_evaluated=evaluated,
        eligible=eligible,
        ineligible=evaluated - eligible,
        queued=queued,
    )