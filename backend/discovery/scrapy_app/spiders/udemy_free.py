import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy_playwright.page import PageMethod

from discovery.scrapy_app.extractors import (
    extract_udemy_course_image,
    extract_udemy_course_language,
    extract_udemy_free_records,
)
from discovery.udemy_catalog import UDEMY_DEFAULT_SEARCH_URL, validate_udemy_catalog_source


class UdemyFreeSpider(scrapy.Spider):
    name = "udemy_free"
    allowed_domains = ["www.udemy.com"]

    def __init__(
        self,
        source_url=UDEMY_DEFAULT_SEARCH_URL,
        max_pages="1",
        item_limit="0",
        render_wait_ms="3500",
        language="en",
        exclude_file="",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.source_url = source_url
        self.max_pages = self._bounded_int(max_pages, "max_pages", 1, 50)
        self.item_limit = self._bounded_int(item_limit, "item_limit", 0, 5000)
        self.render_wait_ms = self._bounded_int(
            render_wait_ms,
            "render_wait_ms",
            0,
            15_000,
        )
        self.language = str(language or "").strip().lower()
        if self.language not in {"", "en"}:
            raise ValueError("language must be blank or en")
        self._accepted = 0
        self._seen_course_keys: set[str] = set()
        self._excluded_course_urls = self._load_excluded_course_urls(exclude_file)
        self._validate_source_url(source_url)

    async def start(self):
        yield self._page_request(1)

    def parse(self, response, **kwargs):
        if self.item_limit and self._accepted >= self.item_limit:
            return
        page_number = self._response_page_number(response)
        records = extract_udemy_free_records(response)

        if not records and self._is_access_challenge(response):
            raise CloseSpider("udemy_access_challenge")

        for record in records:
            record["listing_page_url"] = response.url
            record["source_url"] = self.source_url

        for record in records:
            course_key = str(record.get("url") or record.get("id") or "").strip()
            if not course_key:
                continue
            if course_key in self._seen_course_keys:
                continue
            self._seen_course_keys.add(course_key)
            if str(record.get("url") or "").strip() in self._excluded_course_urls:
                continue

            # English filtering is intentionally performed from the public
            # course page instead of a blocked Udemy ?lang=en URL facet. The
            # same detail request also supplies the image fallback.
            yield scrapy.Request(
                record["url"],
                callback=self.parse_course_detail,
                errback=self.course_detail_failed,
                cb_kwargs={"record": record},
                priority=20,
            )

        if not records:
            self.logger.info(
                "No course cards found on rendered Udemy free page %s; stopping pagination.",
                page_number,
            )
            return

        if self.item_limit and self._accepted >= self.item_limit:
            return

        if page_number >= self.max_pages:
            return

        # Page navigation remains the only query-string use. Udemy's current
        # robots policy explicitly permits ?p= pagination while blocking
        # general faceted query strings.
        yield self._page_request(page_number + 1)

    def parse_course_detail(self, response, record):
        if self.item_limit and self._accepted >= self.item_limit:
            return

        language = extract_udemy_course_language(response)
        if self.language == "en" and not self._is_english(language):
            if language:
                self.logger.info(
                    "Skipping non-English Udemy course %s (%s).",
                    record.get("url"),
                    language,
                )
            else:
                self.logger.info(
                    "Skipping Udemy course %s because the public course language could not be verified.",
                    record.get("url"),
                )
            return

        enriched = dict(record)
        if not enriched.get("image_480x270"):
            enriched["image_480x270"] = extract_udemy_course_image(response)
        enriched["course_language"] = language
        self._accepted += 1
        yield enriched

    def course_detail_failed(self, failure):
        record = dict(failure.request.cb_kwargs["record"])
        if self.language == "en":
            self.logger.info(
                "Skipping Udemy course %s because its public language check failed.",
                record.get("url"),
            )
            return
        if self.item_limit and self._accepted >= self.item_limit:
            return
        self._accepted += 1
        yield record

    # Backward-compatible callback name retained for focused tests and any
    # in-flight task serialized before this patch was applied.
    def parse_course_image(self, response, record):
        yield from self.parse_course_detail(response, record)

    def course_image_failed(self, failure):
        yield from self.course_detail_failed(failure)

    def _page_request(self, page_number: int):
        return scrapy.Request(
            self._page_url(page_number),
            callback=self.parse,
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_timeout", self.render_wait_ms),
                ],
                "playwright_page_goto_kwargs": {
                    "wait_until": "domcontentloaded",
                },
                "learnloot_page_number": page_number,
            },
            priority=-10,
        )

    def _page_url(self, page_number: int) -> str:
        parsed = urlsplit(self.source_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["p"] = str(page_number)
        return urlunsplit(
            (
                "https",
                "www.udemy.com",
                parsed.path,
                urlencode(query),
                "",
            )
        )

    @staticmethod
    def _response_page_number(response) -> int:
        meta_page = response.meta.get("learnloot_page_number")
        if meta_page is not None:
            try:
                parsed_meta = int(meta_page)
            except (TypeError, ValueError):
                parsed_meta = 0
            if parsed_meta >= 1:
                return parsed_meta

        parsed = urlsplit(response.url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        try:
            page_number = int(query.get("p", "1"))
        except (TypeError, ValueError):
            page_number = 1

        return max(page_number, 1)

    @staticmethod
    def _validate_source_url(value: str) -> None:
        validate_udemy_catalog_source(value)

    @staticmethod
    def _is_access_challenge(response) -> bool:
        title = " ".join(response.css("title::text").getall()).strip().lower()
        return title == "just a moment..." or bool(
            response.css("#challenge-running, .cf-challenge, script[src*='challenge-platform']")
        )

    @staticmethod
    def _is_english(value: str) -> bool:
        normalized = " ".join(str(value or "").strip().lower().split())
        return normalized in {"english", "en", "en-us", "en-gb"}

    @staticmethod
    def _load_excluded_course_urls(value: str) -> set[str]:
        path_text = str(value or "").strip()
        if not path_text:
            return set()
        path = Path(path_text)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError("exclude_file must contain a JSON array of course URLs") from exc
        if not isinstance(payload, list):
            raise ValueError("exclude_file must contain a JSON array of course URLs")
        return {
            str(item).strip()
            for item in payload
            if isinstance(item, str) and str(item).strip()
        }

    @staticmethod
    def _bounded_int(value, name: str, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an integer") from exc

        if not minimum <= parsed <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return parsed
