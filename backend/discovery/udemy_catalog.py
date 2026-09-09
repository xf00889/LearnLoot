from urllib.parse import parse_qsl, urlsplit


UDEMY_DEFAULT_SEARCH_URL = (
    "https://www.udemy.com/courses/search/"
    "?q=sql+course&src=sac&price=price-free&lang=en"
)


def normalize_udemy_search_source(
    value: str,
) -> str:
    validate_udemy_catalog_source(value)
    return UDEMY_DEFAULT_SEARCH_URL


def discovery_filters_for_source(source: str) -> dict[str, str | bool]:
    parsed = urlsplit(source)
    if parsed.path != "/courses/search/":
        return {
            "label": "Legacy free catalog",
            "query": "",
            "topic": "",
            "language": "",
            "price": "Free",
            "certification_only": False,
        }

    return {
        "label": "SQL courses · English · Free",
        "query": "sql course",
        "topic": "",
        "language": "English",
        "price": "Free",
        "certification_only": False,
    }


def validate_udemy_catalog_source(value: str) -> None:
    parsed = urlsplit(str(value).strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname != "www.udemy.com"
        or parsed.port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.path != "/courses/search/"
    ):
        raise ValueError(
            "Use a filtered https://www.udemy.com/courses/search/ URL."
        )

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if query.get("price") != "price-free":
        raise ValueError("The Udemy search URL must have Price set to Free.")
