from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy_playwright.page import PageMethod

from discovery.scrapy_app.extractors import extract_udemy_course_image, extract_udemy_free_records
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
        self._emitted = 0
        self._seen_course_keys: set[str] = set()
        self._validate_source_url(source_url)

    async def start(self):
        yield self._page_request(1)

    def parse(self, response, **kwargs):
        page_number = self._response_page_number(response)
        records = extract_udemy_free_records(response)

        if not records and self._is_access_challenge(response):
            raise CloseSpider("udemy_access_challenge")

        for record in records:
            record["listing_page_url"] = response.url
            record["source_url"] = self.source_url

        for record in records:
            course_key = str(record.get("url") or record.get("id") or "").strip()
            if course_key and course_key in self._seen_course_keys:
                continue
            if course_key:
                self._seen_course_keys.add(course_key)
            if self.item_limit and self._emitted >= self.item_limit:
                return
            self._emitted += 1
            if record.get("image_480x270"):
                yield record
                continue
            yield scrapy.Request(
                record["url"],
                callback=self.parse_course_image,
                errback=self.course_image_failed,
                cb_kwargs={"record": record},
                priority=10,
            )

        if not records:
            self.logger.info(
                "No course cards found on rendered Udemy free page %s; stopping pagination.",
                page_number,
            )
            return

        if self.item_limit and self._emitted >= self.item_limit:
            return

        if page_number >= self.max_pages:
            return

        yield self._page_request(page_number + 1)

    def parse_course_image(self, response, record):
        enriched = dict(record)
        enriched["image_480x270"] = extract_udemy_course_image(response)
        yield enriched

    def course_image_failed(self, failure):
        # Course metadata remains valuable even when the optional public detail
        # image lookup is blocked, fails, or is disallowed by robots.txt.
        yield dict(failure.request.cb_kwargs["record"])

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
    def _bounded_int(value, name: str, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an integer") from exc

        if not minimum <= parsed <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return parsed
