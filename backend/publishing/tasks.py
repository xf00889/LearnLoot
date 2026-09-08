from celery import shared_task

from courses.models import Course
from providers.models import Provider

from .delivery import (
    attempt_telegram_delivery,
    get_dispatchable_queue_item_ids,
    mark_retry_exhausted,
    reconcile_stale_sending_deliveries,
)
from .services import evaluate_course_for_publication, evaluate_provider_courses
from .telegram import (
    TelegramAmbiguousError,
    TelegramPermanentError,
    TelegramRateLimitError,
    get_telegram_config,
    telegram_publication_enabled,
)


@shared_task(
    name="publishing.evaluate_provider_publication_candidates",
    acks_late=True,
    reject_on_worker_lost=True,
)
def evaluate_provider_publication_candidates(provider_id: int) -> dict[str, int]:
    try:
        provider = Provider.objects.get(pk=provider_id)
    except Provider.DoesNotExist as exc:
        raise ValueError("provider does not exist") from exc

    result = evaluate_provider_courses(provider)

    if result.queued and telegram_publication_enabled():
        dispatch_queued_telegram_publications.delay(provider.pk)

    return {
        "provider_id": result.provider_id,
        "courses_evaluated": result.courses_evaluated,
        "eligible": result.eligible,
        "ineligible": result.ineligible,
        "queued": result.queued,
    }


@shared_task(
    name="publishing.evaluate_course_publication_candidate",
    acks_late=True,
    reject_on_worker_lost=True,
)
def evaluate_course_publication_candidate(course_id: int) -> dict[str, int | str | bool]:
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist as exc:
        raise ValueError("course does not exist") from exc

    result = evaluate_course_for_publication(course)

    if (
        result.queue_created
        and result.queue_item_id is not None
        and telegram_publication_enabled()
    ):
        publish_telegram_queue_item.delay(result.queue_item_id)

    return {
        "course_id": result.course_id,
        "eligible": result.eligible,
        "score": result.score,
        "queue_item_id": result.queue_item_id or 0,
        "queue_created": result.queue_created,
        "override_applied": result.override_applied,
        "reasons": ",".join(result.reasons),
    }


@shared_task(
    bind=True,
    name="publishing.publish_telegram_queue_item",
    acks_late=True,
    reject_on_worker_lost=True,
)
def publish_telegram_queue_item(self, queue_item_id: int) -> dict[str, int | str | bool]:
    task_id = str(self.request.id or "")

    try:
        result = attempt_telegram_delivery(
            queue_item_id,
            task_id=task_id,
        )
    except TelegramRateLimitError as exc:
        config = get_telegram_config()
        current_retry = int(self.request.retries or 0)

        if current_retry >= config.max_retries:
            mark_retry_exhausted(queue_item_id, task_id=task_id)
            return {
                "queue_item_id": queue_item_id,
                "status": "failed",
                "sent": False,
                "telegram_message_id": 0,
                "detail": "Telegram rate-limit retries were exhausted.",
            }

        exponential_delay = config.retry_base_seconds * (2 ** current_retry)
        countdown = max(int(exc.retry_after), int(exponential_delay))
        raise self.retry(
            exc=exc,
            countdown=countdown,
            max_retries=config.max_retries,
        )
    except TelegramPermanentError as exc:
        return {
            "queue_item_id": queue_item_id,
            "status": "failed",
            "sent": False,
            "telegram_message_id": 0,
            "detail": str(exc),
        }
    except TelegramAmbiguousError as exc:
        return {
            "queue_item_id": queue_item_id,
            "status": "ambiguous",
            "sent": False,
            "telegram_message_id": 0,
            "detail": str(exc),
        }

    return {
        "queue_item_id": result.queue_item_id,
        "status": result.status,
        "sent": result.sent,
        "telegram_message_id": result.telegram_message_id or 0,
        "attempts": result.attempts,
        "detail": result.detail,
    }


@shared_task(
    name="publishing.dispatch_queued_telegram_publications",
    acks_late=True,
    reject_on_worker_lost=True,
)
def dispatch_queued_telegram_publications(
    provider_id: int | None = None,
    limit: int = 50,
) -> dict[str, int | str]:
    if not telegram_publication_enabled():
        return {
            "status": "disabled",
            "dispatched": 0,
        }

    queue_item_ids = get_dispatchable_queue_item_ids(
        provider_id=provider_id,
        limit=limit,
    )
    for queue_item_id in queue_item_ids:
        publish_telegram_queue_item.delay(queue_item_id)

    return {
        "status": "queued",
        "dispatched": len(queue_item_ids),
    }


@shared_task(
    name="publishing.reconcile_stale_telegram_deliveries",
    acks_late=True,
    reject_on_worker_lost=True,
)
def reconcile_stale_telegram_delivery_tasks() -> dict[str, int]:
    return {
        "ambiguous": reconcile_stale_sending_deliveries(),
    }