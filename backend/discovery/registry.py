from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings

from providers.models import Provider

from .providers.base import CourseProvider, ProviderAccessError
from .providers.udemy_free import UdemyFreeConfig, UdemyFreeCourseProvider


class UnsupportedDiscoveryProvider(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class DiscoveryProviderConfig:
    provider_slug: str
    source: str
    access_approved: bool
    max_pages: int
    item_limit: int
    render_wait_ms: int
    currency: str = "USD"


@dataclass(frozen=True, slots=True)
class DiscoveryTarget:
    connector: CourseProvider
    source: str
    config: DiscoveryProviderConfig


def get_discovery_provider_config(provider_slug: str) -> DiscoveryProviderConfig:
    if provider_slug != "udemy":
        raise UnsupportedDiscoveryProvider(
            f"no discovery connector is registered for provider {provider_slug!r}"
        )

    return DiscoveryProviderConfig(
        provider_slug="udemy",
        source=settings.LEARNLOOT_UDEMY_DISCOVERY_SOURCE_URL,
        access_approved=settings.LEARNLOOT_UDEMY_DISCOVERY_ACCESS_APPROVED,
        max_pages=settings.LEARNLOOT_UDEMY_DISCOVERY_MAX_PAGES,
        item_limit=settings.LEARNLOOT_UDEMY_DISCOVERY_ITEM_LIMIT,
        render_wait_ms=settings.LEARNLOOT_UDEMY_DISCOVERY_RENDER_WAIT_MS,
    )


def build_discovery_target(provider: Provider) -> DiscoveryTarget:
    config = get_discovery_provider_config(provider.slug)
    connector = UdemyFreeCourseProvider(
        UdemyFreeConfig(
            access_approved=config.access_approved,
            max_pages=config.max_pages,
            item_limit=config.item_limit,
            render_wait_ms=config.render_wait_ms,
            currency=config.currency,
            catalog_page_url=config.source,
        )
    )
    return DiscoveryTarget(connector=connector, source=config.source, config=config)


def get_discovery_readiness(provider: Provider) -> tuple[bool, str]:
    if provider.status != Provider.Status.ACTIVE:
        return False, "Inactive"

    try:
        target = build_discovery_target(provider)
        target.connector.validate_access()
    except UnsupportedDiscoveryProvider:
        return False, "Unsupported"
    except ProviderAccessError as exc:
        return False, str(exc)
    except (TypeError, ValueError) as exc:
        return False, f"Invalid configuration: {exc}"

    return True, "Ready"


def safe_source_for_display(source: str) -> str:
    """Return a source URL without any accidental user-info component."""

    parsed = urlsplit(source)
    netloc = parsed.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, ""))