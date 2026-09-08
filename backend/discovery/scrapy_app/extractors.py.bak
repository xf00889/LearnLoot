import re
from collections.abc import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

from parsel import Selector


_COURSE_PATH_RE = re.compile(r"^/course/([^/?#]+)/?$")
_RATING_RE = re.compile(r"(?<!\d)([0-5](?:\.\d{1,2})?)(?!\d)")
_REVIEW_RE = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:,\d{3})*|\d+)\s+(?:ratings?|reviews?)\b",
    re.IGNORECASE,
)


def _clean_text(parts: Iterable[str | None]) -> str:
    return " ".join(
        " ".join(part.split())
        for part in parts
        if part and part.strip()
    ).strip()


def _course_url(href: str | None) -> tuple[str, str] | None:
    if not href:
        return None

    absolute = urljoin("https://www.udemy.com", href.strip())
    parsed = urlsplit(absolute)
    if parsed.scheme != "https" or parsed.hostname != "www.udemy.com":
        return None

    match = _COURSE_PATH_RE.match(parsed.path)
    if not match:
        return None

    canonical = urlunsplit(("https", "www.udemy.com", parsed.path, "", ""))
    return canonical, match.group(1)


def _nearest_card(anchor: Selector) -> Selector:
    card = anchor.xpath(
        "ancestor::*["
        "contains(@data-purpose, 'course-card') "
        "or contains(@class, 'course-card') "
        "or self::article "
        "or self::li"
        "][1]"
    )
    if card:
        return card

    fallback = anchor.xpath("ancestor::div[1]")
    return fallback if fallback else anchor


def _looks_like_card_summary(value: str) -> bool:
    normalized = " ".join(value.split())
    lowered = normalized.lower()

    strong_patterns = (
        r"\brating:\s*[0-5](?:\.\d{1,2})?\b",
        r"\b[0-5](?:\.\d{1,2})?\s+out of 5\b",
        r"\b\d[\d,]*\s+(?:ratings?|reviews?)\b",
        r"\b\d+(?:\.\d+)?\s+total hours?\b",
        r"\b\d+(?:\.\d+)?\s+total mins?\b",
        r"\b\d[\d,]*\s+lectures?\b",
    )
    if any(re.search(pattern, lowered) for pattern in strong_patterns):
        return True

    return bool(
        re.search(
            r"\b(?:all levels|beginner|intermediate|expert)\s*$",
            lowered,
        )
        and len(normalized) > 120
    )


def _slug_title(slug: str) -> str:
    words = [part for part in slug.replace("_", "-").split("-") if part]
    return " ".join(word.capitalize() for word in words)


def _title(anchor: Selector, card: Selector, slug: str) -> str:
    # Prefer semantic title hooks. Udemy may use a larger clickable card whose
    # aria-label contains headline, rating, reviews, duration and level.
    selectors = (
        "[data-purpose='course-title-url'] *::text",
        "[data-purpose='course-title-url']::text",
        "[data-purpose='course-title'] *::text",
        "[data-purpose='course-title']::text",
        "[data-testid='course-card-title'] *::text",
        "[data-testid='course-card-title']::text",
    )
    for query in selectors:
        value = _clean_text(card.css(query).getall())
        if value and not _looks_like_card_summary(value):
            return value

    direct = _clean_text(
        [
            anchor.attrib.get("aria-label")
            or anchor.attrib.get("title")
            or ""
        ]
    )
    if direct and not _looks_like_card_summary(direct):
        return direct

    # Some layouts expose a clean heading without the dedicated data-purpose
    # hook. Reject heading text if it has expanded into a full card summary.
    for query in (
        "h3 *::text",
        "h3::text",
        "h2 *::text",
        "h2::text",
    ):
        value = _clean_text(card.css(query).getall())
        if value and not _looks_like_card_summary(value):
            return value

    # Never persist an entire rendered card as the canonical title. The course
    # slug is stable enough for a conservative last-resort display label.
    return _slug_title(slug)


def _external_id(anchor: Selector, slug: str) -> tuple[str, str]:
    values = anchor.xpath(
        "ancestor-or-self::*[@data-course-id][1]/@data-course-id"
        " | ancestor-or-self::*[@data-courseid][1]/@data-courseid"
    ).getall()
    for value in values:
        text = str(value).strip()
        if text.isdigit():
            return text, "numeric"

    return f"slug:{slug}", "slug"


def _instructor(card: Selector) -> str:
    queries = (
        "[data-purpose*='instructor'] *::text",
        "[data-purpose*='instructor']::text",
        "[class*='instructor'] *::text",
        "[class*='instructor']::text",
    )
    for query in queries:
        value = _clean_text(card.css(query).getall())
        if value:
            return value
    return ""


def _rating(card: Selector) -> str | None:
    labels = card.xpath(
        ".//@aria-label["
        "contains(translate(., 'RATING', 'rating'), 'rating')"
        "]"
    ).getall()
    for label in labels:
        match = _RATING_RE.search(label)
        if match:
            return match.group(1)

    rating_text = _clean_text(
        card.css("[data-purpose*='rating'] *::text").getall()
        + card.css("[data-purpose*='rating']::text").getall()
    )
    match = _RATING_RE.search(rating_text)
    return match.group(1) if match else None


def _review_count(card: Selector) -> int | None:
    text = _clean_text(card.xpath(".//text()").getall())
    match = _REVIEW_RE.search(text)
    if not match:
        return None

    digits = match.group(1).replace(",", "")
    return int(digits)


def _thumbnail(card: Selector) -> str:
    src = card.css("img::attr(src)").get()
    if src:
        return urljoin("https://www.udemy.com", src)

    srcset = card.css("img::attr(srcset)").get()
    if not srcset:
        return ""

    first = srcset.split(",", 1)[0].strip().split(" ", 1)[0]
    return urljoin("https://www.udemy.com", first) if first else ""


def extract_udemy_free_records(response) -> list[dict]:
    """Extract public course-card metadata from a rendered Udemy free catalog page."""

    records: list[dict] = []
    seen_urls: set[str] = set()

    for anchor in response.css("a[href*='/course/']"):
        resolved = _course_url(anchor.attrib.get("href"))
        if resolved is None:
            continue

        canonical_url, slug = resolved
        if canonical_url in seen_urls:
            continue

        card = _nearest_card(anchor)
        title = _title(anchor, card, slug)
        if not title:
            continue

        external_id, identity_kind = _external_id(anchor, slug)
        instructor = _instructor(card)

        records.append(
            {
                "id": external_id,
                "identity_kind": identity_kind,
                "title": title,
                "url": canonical_url,
                "image_480x270": _thumbnail(card),
                "visible_instructors": (
                    [{"display_name": instructor}]
                    if instructor
                    else []
                ),
                "avg_rating": _rating(card),
                "num_reviews": _review_count(card),
                "num_subscribers": None,
                "headline": "",
                "is_paid": False,
                "catalog_kind": "free",
                "source_url": response.url,
                "source_type": "udemy_free_catalog_scrapy",
            }
        )
        seen_urls.add(canonical_url)

    return records