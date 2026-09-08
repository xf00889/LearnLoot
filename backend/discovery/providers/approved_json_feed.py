from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urljoin, urlparse

from discovery.contracts import CourseCandidate, DiscoveryIdentity, NormalizedCourse
from discovery.http import JsonHttpClient

from .base import CourseProvider, ProviderAccessError, RawCourse


@dataclass(frozen=True, slots=True)
class ApprovedFeedConfig:
    provider_key: str
    access_approved: bool
    headers: Mapping[str, str] = field(default_factory=dict, repr=False)
    max_pages: int = 25
    detail_url_template: str | None = None


class ApprovedJsonFeedProvider(CourseProvider):
    """
    Connector for an explicitly approved HTTPS JSON feed.

    This class does not grant permission to collect data from a provider. The operator must
    set access_approved=True only for a feed/API that is actually permitted for automated
    access. Ordinary website HTML pages are intentionally not supported by this connector.
    """

    def __init__(
        self,
        config: ApprovedFeedConfig,
        *,
        client: JsonHttpClient | None = None,
    ) -> None:
        self.config = config
        self.key = config.provider_key.strip()
        self._headers = dict(config.headers)
        self._client = client or JsonHttpClient()

    def validate_access(self) -> None:
        if not self.key:
            raise ProviderAccessError("provider_key is required")
        if not self.config.access_approved:
            raise ProviderAccessError("automated access has not been approved for this feed")
        if not 1 <= self.config.max_pages <= 100:
            raise ProviderAccessError("max_pages must be between 1 and 100")
        if self.config.detail_url_template is not None:
            if "{external_id}" not in self.config.detail_url_template:
                raise ProviderAccessError(
                    "detail_url_template must contain the {external_id} placeholder"
                )
            self._validate_https_url(self.config.detail_url_template.replace("{external_id}", "test"))

    def discover(self, source: str) -> Iterable[RawCourse]:
        self._validate_https_url(source)
        origin = self._origin(source)
        page_url = source
        seen_urls: set[str] = set()

        for _page_number in range(1, self.config.max_pages + 1):
            if page_url in seen_urls:
                raise ValueError("provider pagination entered a loop")
            seen_urls.add(page_url)

            payload = self._client.get_json(page_url, self._headers)
            results = payload.get("results")
            if not isinstance(results, list):
                raise ValueError("provider feed results must be a list")

            for raw_course in results:
                if not isinstance(raw_course, Mapping):
                    raise ValueError("provider feed course entries must be JSON objects")
                record = dict(raw_course)
                record.setdefault("source_url", page_url)
                record.setdefault("source_type", "partner_feed")
                yield record

            next_value = payload.get("next")
            if next_value in (None, ""):
                return
            if not isinstance(next_value, str):
                raise ValueError("provider feed next value must be a URL string or null")

            next_url = urljoin(page_url, next_value)
            self._validate_https_url(next_url)
            if self._origin(next_url) != origin:
                raise ValueError("provider pagination attempted to leave the approved origin")
            page_url = next_url

        raise ValueError("provider pagination exceeded the configured page limit")

    def identify(self, raw_course: RawCourse, source: str) -> DiscoveryIdentity:
        external_id = str(raw_course.get("id") or "").strip()
        source_url = str(raw_course.get("source_url") or source).strip()
        return DiscoveryIdentity(external_id=external_id, source_url=source_url)

    def parse(self, raw_course: RawCourse, source: str) -> CourseCandidate:
        offer = raw_course.get("offer", {})
        if not isinstance(offer, Mapping):
            raise ValueError("provider feed offer must be a JSON object")

        return CourseCandidate(
            external_id=self._optional_text(raw_course.get("id")),
            title=self._optional_text(raw_course.get("title")),
            canonical_url=self._optional_text(raw_course.get("url")),
            source_url=self._optional_text(raw_course.get("source_url")) or source,
            source_type=self._optional_text(raw_course.get("source_type")) or "partner_feed",
            thumbnail_url=self._optional_text(raw_course.get("thumbnail_url")),
            instructor_name=self._optional_text(raw_course.get("instructor_name")),
            rating=raw_course.get("rating"),
            review_count=raw_course.get("review_count"),
            student_count=raw_course.get("student_count"),
            duration_minutes=raw_course.get("duration_minutes"),
            description=self._optional_text(raw_course.get("description")),
            price_amount=offer.get("amount"),
            currency=self._optional_text(offer.get("currency")),
            is_free=offer.get("is_free", False),
            price_type=self._optional_text(offer.get("type")),
        )

    def fetch_course(self, external_id: str) -> RawCourse:
        template = self.config.detail_url_template
        if template is None:
            raise ProviderAccessError("detail_url_template is not configured")

        detail_url = template.format(external_id=quote(external_id, safe=""))
        self._validate_https_url(detail_url)
        payload = self._client.get_json(detail_url, self._headers)
        return payload

    def build_destination_url(self, course: NormalizedCourse) -> str:
        return course.canonical_url

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _validate_https_url(value: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("approved provider feed URLs must use absolute HTTPS URLs")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("provider feed credentials must not be embedded in URLs")

    @staticmethod
    def _origin(value: str) -> tuple[str, str, int | None]:
        parsed = urlparse(value)
        return parsed.scheme.lower(), parsed.hostname or "", parsed.port