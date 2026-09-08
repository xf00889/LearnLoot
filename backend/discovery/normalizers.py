from decimal import Decimal, InvalidOperation

from .contracts import CourseCandidate, NormalizedCourse, NumberLike


class CourseNormalizationError(ValueError):
    pass


def _clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_decimal(value: NumberLike | None, field_name: str) -> Decimal | None:
    if value is None or value == "":
        return None

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise CourseNormalizationError(f"{field_name} must be numeric") from exc

    if not result.is_finite():
        raise CourseNormalizationError(f"{field_name} must be finite")

    return result


def _to_non_negative_int(value: int | str | None, field_name: str) -> int | None:
    if value is None or value == "":
        return None

    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise CourseNormalizationError(f"{field_name} must be an integer") from exc

    if result < 0:
        raise CourseNormalizationError(f"{field_name} cannot be negative")

    return result


def _to_bool(value: bool | str | int) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "free"}:
        return True
    if normalized in {"0", "false", "no", "n", "paid", ""}:
        return False

    raise CourseNormalizationError("is_free must be a boolean-like value")


def normalize_candidate(candidate: CourseCandidate) -> NormalizedCourse:
    is_free = _to_bool(candidate.is_free)
    amount = _to_decimal(candidate.price_amount, "price_amount")
    if is_free:
        amount = Decimal("0.00")

    rating = _to_decimal(candidate.rating, "rating")
    try:
        if rating is not None:
            rating = rating.quantize(Decimal("0.01"))
        if amount is not None:
            amount = amount.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise CourseNormalizationError("numeric value cannot be represented") from exc

    return NormalizedCourse(
        external_id=_clean_text(candidate.external_id),
        title=_clean_text(candidate.title),
        canonical_url=_clean_text(candidate.canonical_url),
        source_url=_clean_text(candidate.source_url),
        source_type=_clean_text(candidate.source_type) or "listing",
        thumbnail_url=_clean_text(candidate.thumbnail_url),
        instructor_name=_clean_text(candidate.instructor_name),
        rating=rating,
        review_count=_to_non_negative_int(candidate.review_count, "review_count"),
        student_count=_to_non_negative_int(candidate.student_count, "student_count"),
        duration_minutes=_to_non_negative_int(
            candidate.duration_minutes,
            "duration_minutes",
        ),
        description=_clean_text(candidate.description),
        price_amount=amount,
        currency=_clean_text(candidate.currency).upper(),
        is_free=is_free,
        price_type=_clean_text(candidate.price_type),
    )