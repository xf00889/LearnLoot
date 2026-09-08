from decimal import Decimal
from urllib.parse import urlparse

from .contracts import NormalizedCourse


class CourseValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_course(course: NormalizedCourse) -> None:
    errors: list[str] = []

    if not course.external_id:
        errors.append("external_id is required")
    elif len(course.external_id) > 100:
        errors.append("external_id exceeds 100 characters")

    if not course.title:
        errors.append("title is required")
    elif len(course.title) > 500:
        errors.append("title exceeds 500 characters")

    if not _is_http_url(course.canonical_url):
        errors.append("canonical_url must be an absolute HTTP(S) URL")

    if not _is_http_url(course.source_url):
        errors.append("source_url must be an absolute HTTP(S) URL")

    if not course.source_type:
        errors.append("source_type is required")
    elif len(course.source_type) > 50:
        errors.append("source_type exceeds 50 characters")

    if len(course.instructor_name) > 255:
        errors.append("instructor_name exceeds 255 characters")

    if course.rating is not None and not 0 <= course.rating <= 5:
        errors.append("rating must be between 0 and 5")

    if len(course.currency) != 3 or not course.currency.isalpha():
        errors.append("currency must be a three-letter code")

    if not course.is_free and course.price_amount is None:
        errors.append("price_amount is required for non-free courses")
    if course.price_amount is not None and course.price_amount < 0:
        errors.append("price_amount cannot be negative")
    if course.price_amount is not None and course.price_amount > Decimal("9999999999.99"):
        errors.append("price_amount exceeds the database precision")

    for field_name, value in (
        ("review_count", course.review_count),
        ("student_count", course.student_count),
        ("duration_minutes", course.duration_minutes),
    ):
        if value is not None and value > 2_147_483_647:
            errors.append(f"{field_name} exceeds the database integer range")

    if len(course.price_type) > 30:
        errors.append("price_type exceeds 30 characters")

    if errors:
        raise CourseValidationError(errors)