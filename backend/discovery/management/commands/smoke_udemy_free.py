from django.core.management.base import BaseCommand, CommandError

from discovery.normalizers import normalize_candidate
from discovery.providers.base import ProviderAccessError
from discovery.providers.udemy_free import UdemyFreeConfig, UdemyFreeCourseProvider
from discovery.scrapy_app.runner import ScrapyCrawlerError
from discovery.udemy_catalog import UDEMY_DEFAULT_SEARCH_URL
from discovery.validators import validate_course


class Command(BaseCommand):
    help = "Perform a read-only Scrapy/Playwright smoke check of Udemy free courses."

    def add_arguments(self, parser):
        parser.add_argument(
            "--acknowledge-access-terms",
            action="store_true",
            help="Required acknowledgement that the operator has reviewed current access terms.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Number of rendered free-course records to validate (1-20).",
        )
        parser.add_argument(
            "--render-wait-ms",
            type=int,
            default=3500,
            help="Browser render wait after DOM content load (0-15000 ms).",
        )

    def handle(self, *args, **options):
        if not options["acknowledge_access_terms"]:
            raise CommandError(
                "Refusing live Udemy access without --acknowledge-access-terms"
            )

        limit = options["limit"]
        if not 1 <= limit <= 20:
            raise CommandError("--limit must be between 1 and 20")

        render_wait_ms = options["render_wait_ms"]
        if not 0 <= render_wait_ms <= 15_000:
            raise CommandError("--render-wait-ms must be between 0 and 15000")

        source = UDEMY_DEFAULT_SEARCH_URL
        connector = UdemyFreeCourseProvider(
            UdemyFreeConfig(
                access_approved=True,
                max_pages=1,
                item_limit=limit,
                render_wait_ms=render_wait_ms,
            )
        )

        try:
            connector.validate_access()
            validated = 0
            for raw_course in connector.discover(source):
                candidate = connector.parse(raw_course, source)
                normalized = normalize_candidate(candidate)
                validate_course(normalized)
                validated += 1
                self.stdout.write(
                    f"{normalized.external_id}: {normalized.title} | "
                    f"rating={normalized.rating or 'n/a'} | "
                    f"reviews={normalized.review_count if normalized.review_count is not None else 'n/a'} "
                    f"-> {normalized.canonical_url}"
                )
                if validated >= limit:
                    break
        except (ProviderAccessError, ScrapyCrawlerError, ValueError) as exc:
            raise CommandError(
                f"UDEMY_FREE_SMOKE=BLOCKED ({type(exc).__name__}: {exc})"
            ) from exc

        if validated == 0:
            raise CommandError(
                "UDEMY_FREE_SMOKE=NO_RECORDS "
                "(the public page loaded but no rendered course cards were extracted)"
            )

        self.stdout.write(
            self.style.SUCCESS(f"UDEMY_FREE_SMOKE=PASS ({validated} courses)")
        )
