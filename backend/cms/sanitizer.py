from __future__ import annotations

import nh3


_RICH_TEXT_CLEANER = nh3.Cleaner(
    tags={
        "p", "br", "h2", "h3", "h4", "h5", "h6", "strong", "em", "u", "s",
        "ul", "ol", "li", "blockquote", "pre", "code", "a", "figure", "figcaption",
        "img", "table", "thead", "tbody", "tr", "th", "td", "hr", "span",
    },
    clean_content_tags={"script", "style", "iframe", "object", "embed", "form"},
    attributes={
        "a": {"href", "title", "target"},
        "img": {"src", "alt", "width", "height"},
        "figure": {"style"},
        "th": {"colspan", "rowspan"},
        "td": {"colspan", "rowspan"},
    },
    allowed_classes={
        "figure": {"image", "image_resized", "image-style-side", "image-style-align-left", "image-style-align-right", "table"},
        "table": {"table"},
    },
    filter_style_properties={"width", "height"},
    url_schemes={"http", "https", "mailto"},
    link_rel="noopener noreferrer",
)


def sanitize_rich_html(value: str | None) -> str:
    return _RICH_TEXT_CLEANER.clean((value or "").strip())
