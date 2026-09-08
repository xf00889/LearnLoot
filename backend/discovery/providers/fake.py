from collections.abc import Iterable, Mapping
from typing import Any

from discovery.contracts import CourseCandidate, DiscoveryIdentity, NormalizedCourse

from .base import CourseProvider, ProviderAccessError, RawCourse


class FakeCourseProvider(CourseProvider):
    """Deterministic provider used to prove the discovery pipeline without network I/O."""

    key = "fake"

    def __init__(
        self,
        records: Iterable[RawCourse] = (),
        *,
        access_error: str | None = None,
        discovery_error: Exception | None = None,
    ) -> None:
        self._records = tuple(records)
        self._access_error = access_error
        self._discovery_error = discovery_error

    def validate_access(self) -> None:
        if self._access_error:
            raise ProviderAccessError(self._access_error)

    def discover(self, source: str) -> Iterable[RawCourse]:
        del source
        if self._discovery_error is not None:
            raise self._discovery_error
        return iter(self._records)

    def identify(self, raw_course: RawCourse, source: str) -> DiscoveryIdentity:
        course = raw_course.get("course")
        if not isinstance(course, Mapping):
            return DiscoveryIdentity(external_id="", source_url=source)

        external_id = str(course.get("id") or "").strip()
        source_url = str(raw_course.get("source_url") or source).strip()
        return DiscoveryIdentity(external_id=external_id, source_url=source_url)

    def parse(self, raw_course: RawCourse, source: str) -> CourseCandidate:
        course = raw_course.get("course")
        offer = raw_course.get("offer", {})
        if not isinstance(course, Mapping):
            raise ValueError("fake record must contain a course mapping")
        if not isinstance(offer, Mapping):
            raise ValueError("fake record offer must be a mapping")

        return CourseCandidate(
            external_id=self._optional_text(course.get("id")),
            title=self._optional_text(course.get("name")),
            canonical_url=self._optional_text(course.get("url")),
            source_url=self._optional_text(raw_course.get("source_url")) or source,
            source_type=self._optional_text(raw_course.get("source_type")) or "listing",
            thumbnail_url=self._optional_text(course.get("thumbnail")),
            instructor_name=self._optional_text(course.get("instructor")),
            rating=course.get("rating"),
            review_count=course.get("reviews"),
            student_count=course.get("students"),
            duration_minutes=course.get("duration_minutes"),
            description=self._optional_text(course.get("description")),
            price_amount=offer.get("amount"),
            currency=self._optional_text(offer.get("currency")),
            is_free=offer.get("is_free", False),
            price_type=self._optional_text(offer.get("type")),
        )

    def fetch_course(self, external_id: str) -> RawCourse:
        for record in self._records:
            identity = self.identify(record, "")
            if identity.external_id == external_id:
                return record
        raise KeyError(external_id)

    def build_destination_url(self, course: NormalizedCourse) -> str:
        return course.canonical_url

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)