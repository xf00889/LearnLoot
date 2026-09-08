from dataclasses import dataclass
from decimal import Decimal


NumberLike = Decimal | int | float | str


@dataclass(frozen=True, slots=True)
class DiscoveryIdentity:
    external_id: str
    source_url: str


@dataclass(frozen=True, slots=True)
class CourseCandidate:
    external_id: str | None
    title: str | None
    canonical_url: str | None
    source_url: str | None
    source_type: str | None = "listing"
    thumbnail_url: str | None = ""
    instructor_name: str | None = ""
    rating: NumberLike | None = None
    review_count: int | str | None = None
    student_count: int | str | None = None
    duration_minutes: int | str | None = None
    description: str | None = ""
    price_amount: NumberLike | None = None
    currency: str | None = None
    is_free: bool | str | int = False
    price_type: str | None = ""


@dataclass(frozen=True, slots=True)
class NormalizedCourse:
    external_id: str
    title: str
    canonical_url: str
    source_url: str
    source_type: str
    thumbnail_url: str
    instructor_name: str
    rating: Decimal | None
    review_count: int | None
    student_count: int | None
    duration_minutes: int | None
    description: str
    price_amount: Decimal | None
    currency: str
    is_free: bool
    price_type: str