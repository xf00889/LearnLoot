import re
from urllib.parse import parse_qsl, unquote_plus, urlsplit


UDEMY_DEFAULT_SEARCH_URL = "https://www.udemy.com/courses/free/"
_FREE_CATALOG_PATH = "/courses/free/"
_LEGACY_SEARCH_PATH = "/courses/search/"
_TOPIC_PATH_RE = re.compile(r"^/topic/([a-z0-9][a-z0-9-]{0,99})/free/$")
_TOPIC_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")

_TOPIC_DISPLAY_NAMES = {
    "c-plus-plus": "C++",
    "c-sharp": "C#",
    "javascript": "JavaScript",
    "mysql": "MySQL",
    "nodejs": "Node.js",
    "sql": "SQL",
}

_TOPIC_ALIASES = {
    "c#": "c-sharp",
    "c sharp": "c-sharp",
    "c++": "c-plus-plus",
    "c plus plus": "c-plus-plus",
    "excel": "excel",
    "javascript": "javascript",
    "java script": "javascript",
    "js": "javascript",
    "microsoft excel": "excel",
    "mysql": "mysql",
    "node": "nodejs",
    "node.js": "nodejs",
    "node js": "nodejs",
    "nodejs": "nodejs",
    "python": "python",
    "react": "react",
    "sql": "sql",
}


def _parsed_udemy_url(value: str):
    parsed = urlsplit(str(value).strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname != "www.udemy.com"
        or parsed.port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("Use a public https://www.udemy.com Udemy catalog URL.")
    return parsed


def normalize_udemy_topic(value: str) -> str:
    text = " ".join(str(value or "").strip().lower().split())
    if not text:
        return ""
    if text in _TOPIC_ALIASES:
        return _TOPIC_ALIASES[text]

    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if not _TOPIC_SLUG_RE.fullmatch(slug):
        raise ValueError("Topic must contain letters, numbers, spaces, or hyphens.")
    return slug


def _legacy_topic(query: dict[str, str]) -> str:
    raw = unquote_plus(str(query.get("q") or "")).strip()
    if not raw:
        return ""
    # The old default was "sql course". Strip only a trailing generic word;
    # do not guess numeric courseLabel facets or silently reinterpret queries.
    simplified = re.sub(r"\s+courses?$", "", raw, flags=re.IGNORECASE).strip()
    return normalize_udemy_topic(simplified)


def build_udemy_discovery_source(*, topic: str = "", certification_only: bool = False) -> str:
    if certification_only:
        raise ValueError(
            "Certification Prep discovery is not enabled yet. Udemy's public certification browse page mixes paid and free courses, and LearnLoot will not label paid courses as free just to emulate a blocked URL facet."
        )

    topic_slug = normalize_udemy_topic(topic)
    if not topic_slug:
        return UDEMY_DEFAULT_SEARCH_URL
    return f"https://www.udemy.com/topic/{topic_slug}/free/"


def normalize_udemy_search_source(value: str) -> str:
    """Normalize supported inputs to robots-compatible public free-course paths."""

    parsed = _parsed_udemy_url(value)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))

    if parsed.path == _FREE_CATALOG_PATH:
        _validate_page_query(query, "The Udemy free catalog URL")
        return UDEMY_DEFAULT_SEARCH_URL

    topic_match = _TOPIC_PATH_RE.fullmatch(parsed.path)
    if topic_match:
        _validate_page_query(query, "The Udemy free topic URL")
        return f"https://www.udemy.com/topic/{topic_match.group(1)}/free/"

    # Backward compatibility only: convert an old Price=Free search source to
    # an equivalent no-facet public topic/free path when its textual query can
    # be represented safely. The crawler itself never receives /courses/search/.
    if parsed.path == _LEGACY_SEARCH_PATH:
        if query.get("price") != "price-free":
            raise ValueError("The legacy Udemy search URL must have Price set to Free.")
        if query.get("lang") not in (None, "", "en"):
            raise ValueError(
                "Udemy discovery currently supports English only; LearnLoot verifies English from each public course page instead of using the blocked lang facet."
            )
        if str(query.get("cert_topic") or "").strip().lower() not in {"", "false", "0"}:
            raise ValueError(
                "Certification Prep discovery is not enabled yet. The blocked cert_topic facet is not silently dropped."
            )
        if query.get("courseLabel"):
            raise ValueError(
                "Udemy courseLabel IDs are blocked URL facets and are not guessed by LearnLoot. Select the public topic name instead."
            )
        supported_legacy_keys = {"q", "src", "price", "lang", "p", "cert_topic"}
        unsupported = sorted(set(query) - supported_legacy_keys)
        if unsupported:
            raise ValueError(
                "Unsupported Udemy search facets cannot be converted safely: "
                + ", ".join(unsupported)
                + ". Use a public topic name and LearnLoot's local filters instead."
            )
        return build_udemy_discovery_source(topic=_legacy_topic(query))

    raise ValueError(
        "Use https://www.udemy.com/courses/free/ or a public https://www.udemy.com/topic/<topic>/free/ URL for Udemy discovery."
    )


def _validate_page_query(query: dict[str, str], label: str) -> None:
    if not query:
        return
    if set(query) != {"p"}:
        raise ValueError(f"{label} may only contain a page parameter.")
    try:
        page = int(query["p"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} page must be a positive integer.") from exc
    if page < 1:
        raise ValueError(f"{label} page must be a positive integer.")


def discovery_filters_for_source(source: str) -> dict[str, str | bool]:
    parsed = urlsplit(source)
    topic_match = _TOPIC_PATH_RE.fullmatch(parsed.path)
    topic_slug = topic_match.group(1) if topic_match else ""
    topic = (
        _TOPIC_DISPLAY_NAMES.get(topic_slug, topic_slug.replace("-", " ").title())
        if topic_slug
        else ""
    )
    label_topic = topic or "All topics"
    return {
        "label": f"{label_topic} · English · Free",
        "query": "",
        "topic": topic,
        "language": "English",
        "price": "Free",
        "certification_only": False,
    }


def validate_udemy_catalog_source(value: str) -> None:
    """Allow only robots-compatible public free catalog/topic sources."""

    parsed = _parsed_udemy_url(value)
    if parsed.path != _FREE_CATALOG_PATH and not _TOPIC_PATH_RE.fullmatch(parsed.path):
        raise ValueError(
            "Use the public /courses/free/ catalog or a /topic/<topic>/free/ page for live Udemy crawling."
        )

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    _validate_page_query(query, "The live Udemy source URL")
