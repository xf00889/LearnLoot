from celery import shared_task

from providers.models import Provider
from publishing.tasks import evaluate_provider_publication_candidates

from .models import DiscoveryRun
from .registry import build_discovery_target
from .services import execute_discovery


@shared_task(
    name="discovery.run_provider_discovery",
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_provider_discovery(provider_id: int) -> dict[str, int | str]:
    try:
        provider = Provider.objects.get(pk=provider_id)
    except Provider.DoesNotExist as exc:
        raise ValueError("provider does not exist") from exc

    if provider.status != Provider.Status.ACTIVE:
        return {
            "provider_id": provider.pk,
            "run_id": 0,
            "status": "skipped",
            "records_found": 0,
            "records_new": 0,
            "records_updated": 0,
            "records_failed": 0,
        }

    target = build_discovery_target(provider)
    run = execute_discovery(provider, target.connector, target.source)

    if run.status == DiscoveryRun.Status.SUCCEEDED:
        evaluate_provider_publication_candidates.delay(provider.pk)

    return {
        "provider_id": provider.pk,
        "run_id": run.pk,
        "status": run.status,
        "records_found": run.records_found,
        "records_new": run.records_new,
        "records_updated": run.records_updated,
        "records_failed": run.records_failed,
    }