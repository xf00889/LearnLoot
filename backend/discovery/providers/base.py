from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import Any

from discovery.contracts import (
    CourseCandidate,
    DiscoveryIdentity,
    NormalizedCourse,
)
from discovery.normalizers import normalize_candidate


RawCourse = Mapping[str, Any]


class ProviderAccessError(RuntimeError):
    pass


class CourseProvider(ABC):
    key: str

    @abstractmethod
    def validate_access(self) -> None:
        """Raise ProviderAccessError when discovery is not currently permitted."""

    @abstractmethod
    def discover(self, source: str) -> Iterable[RawCourse]:
        """Yield provider-specific raw records for one configured source."""

    @abstractmethod
    def identify(self, raw_course: RawCourse, source: str) -> DiscoveryIdentity:
        """Extract the minimal identity needed for discovery-run auditing."""

    @abstractmethod
    def parse(self, raw_course: RawCourse, source: str) -> CourseCandidate:
        """Translate provider-specific structure into a provider-neutral candidate."""

    def normalize(self, raw_course: RawCourse, source: str) -> NormalizedCourse:
        return normalize_candidate(self.parse(raw_course, source))

    @abstractmethod
    def fetch_course(self, external_id: str) -> RawCourse:
        """Fetch one provider record by its provider-specific course identifier."""

    @abstractmethod
    def build_destination_url(self, course: NormalizedCourse) -> str:
        """Build the provider destination URL for an already-normalized course."""