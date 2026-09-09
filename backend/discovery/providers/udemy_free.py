from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

from discovery.contracts import CourseCandidate, DiscoveryIdentity, NormalizedCourse
from discovery.scrapy_app.runner import ScrapyUdemySource
from discovery.udemy_catalog import UDEMY_DEFAULT_SEARCH_URL, validate_udemy_catalog_source

from .base import CourseProvider, ProviderAccessError, RawCourse


_UDEMY_HOST = "www.udemy.com"
@dataclass(frozen=True, slots=True)
class UdemyFreeConfig:
    access_approved: bool = False
    max_pages: int = 10
    item_limit: int = 0
    render_wait_ms: int = 3500
    currency: str = "USD"
    catalog_page_url: str = UDEMY_DEFAULT_SEARCH_URL


class UdemyFreeCourseProvider(CourseProvider):
    """Provider adapter for Scrapy-rendered public Udemy free-course records."""

    key = "udemy"

    def __init__(
        self,
        config: UdemyFreeConfig,
        *,
        crawler: ScrapyUdemySource | None = None,
    ) -> None:
        self.config = config
        self._crawler = crawler or ScrapyUdemySource()

    def validate_access(self) -> None:
        if not self.config.access_approved:
            raise ProviderAccessError(
                "Udemy automated catalog access has not been acknowledged as permitted"
            )
        if not 1 <= self.config.max_pages <= 50:
            raise ProviderAccessError("max_pages must be between 1 and 50")
        if not 0 <= self.config.item_limit <= 5000:
            raise ProviderAccessError("item_limit must be between 0 and 5000")
        if not 0 <= self.config.render_wait_ms <= 15_000:
            raise ProviderAccessError("render_wait_ms must be between 0 and 15000")

        currency = self.config.currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ProviderAccessError("currency must be a three-letter code")

        self._validate_catalog_source(self.config.catalog_page_url)

    def discover(self, source: str) -> Iterable[RawCourse]:
        self._validate_catalog_source(source)

        for raw_course in self._crawler.crawl(
            source,
            max_pages=self.config.max_pages,
            item_limit=self.config.item_limit,
            render_wait_ms=self.config.render_wait_ms,
        ):
            if not isinstance(raw_course, Mapping):
                raise ValueError("Udemy Scrapy records must be objects")
            if raw_course.get("catalog_kind") != "free":
                continue
            if raw_course.get("is_paid") is not False:
                continue
            yield raw_course

    def identify(self, raw_course: RawCourse, source: str) -> DiscoveryIdentity:
        external_id = str(raw_course.get("id") or "").strip()
        source_url = str(raw_course.get("source_url") or source).strip()
        return DiscoveryIdentity(external_id=external_id, source_url=source_url)

    def parse(self, raw_course: RawCourse, source: str) -> CourseCandidate:
        if raw_course.get("catalog_kind") != "free":
            raise ValueError("Udemy record did not originate from the free catalog")
        if raw_course.get("is_paid") is not False:
            raise ValueError("Udemy record is not explicitly marked as a free course")

        canonical_url = self._absolute_course_url(raw_course.get("url"))
        instructor_name = self._instructor_name(raw_course.get("visible_instructors"))
        thumbnail_url = self._optional_text(
            raw_course.get("image_480x270") or raw_course.get("image_240x135")
        )

        return CourseCandidate(
            external_id=self._optional_text(raw_course.get("id")),
            title=self._optional_text(raw_course.get("title")),
            canonical_url=canonical_url,
            source_url=self._optional_text(raw_course.get("source_url")) or source,
            source_type=self._optional_text(raw_course.get("source_type"))
            or "udemy_free_catalog_scrapy",
            thumbnail_url=thumbnail_url,
            instructor_name=instructor_name,
            rating=raw_course.get("avg_rating"),
            review_count=raw_course.get("num_reviews"),
            student_count=raw_course.get("num_subscribers"),
            duration_minutes=None,
            description=self._optional_text(raw_course.get("headline")),
            price_amount="0.00",
            currency=self.config.currency.strip().upper(),
            is_free=True,
            price_type="free",
        )

    def fetch_course(self, external_id: str) -> RawCourse:
        raise ProviderAccessError(
            "individual Udemy course fetching is not enabled; use the public free-catalog spider"
        )

    def build_destination_url(self, course: NormalizedCourse) -> str:
        return course.canonical_url

    @staticmethod
    def _validate_catalog_source(value: str) -> None:
        validate_udemy_catalog_source(value)

    @staticmethod
    def _absolute_course_url(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        absolute = urljoin("https://www.udemy.com", text)
        parsed = urlparse(absolute)
        if parsed.scheme != "https" or parsed.hostname != _UDEMY_HOST:
            raise ValueError("Udemy course URL must remain on www.udemy.com")
        if not parsed.path.startswith("/course/"):
            raise ValueError("Udemy course URL must use the /course/ path")
        return f"https://www.udemy.com{parsed.path}"

    @staticmethod
    def _instructor_name(value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("visible_instructors must be a list")

        names: list[str] = []
        for item in value:
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("display_name") or item.get("title") or "").strip()
            if name:
                names.append(name)

        return ", ".join(names) or None

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip()
