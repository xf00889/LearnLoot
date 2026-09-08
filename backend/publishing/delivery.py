from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
import hmac

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import PublicationQueueItem, TelegramPost
from .services import evaluate_course_for_publication
from .telegram import (
    TelegramAmbiguousError,
    TelegramBotClient,
    TelegramConfigurationError,
    TelegramPermanentError,
    TelegramRateLimitError,
    build_course_landing_url,
    get_telegram_config,
    render_telegram_course_message,
    validate_telegram_config,
)


@dataclass(frozen=True, slots=True)
class TelegramDeliveryResult:
    queue_item_id: int
    status: str
    sent: bool
    telegram_message_id: int | None
    attempts: int
    detail: str


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _target_fingerprint(channel_id: str) -> str:
    key = str(settings.SECRET_KEY).encode("utf-8")
    return hmac.new(key, channel_id.encode("utf-8"), hashlib.sha256).hexdigest()


def _result(
    queue_item: PublicationQueueItem,
    *,
    status: str,
    detail: str,
    sent: bool = False,
    telegram_message_id: int | None = None,
    attempts: int | None = None,
) -> TelegramDeliveryResult:
    return TelegramDeliveryResult(
        queue_item_id=queue_item.pk,
        status=status,
        sent=sent,
        telegram_message_id=telegram_message_id,
        attempts=queue_item.attempts if attempts is None else attempts,
        detail=detail,
    )


def _load_queue_item(queue_item_id: int) -> PublicationQueueItem:
    try:
        return PublicationQueueItem.objects.select_related(
            "course__provider",
            "latest_price",
        ).get(pk=queue_item_id)
    except PublicationQueueItem.DoesNotExist as exc:
        raise ValueError("publication queue item does not exist") from exc


def _snapshot_defaults(queue_item: PublicationQueueItem, *, channel_id: str, public_base_url: str):
    course = queue_item.course
    landing_url = build_course_landing_url(course, public_base_url=public_base_url)
    message_text = render_telegram_course_message(course, landing_url=landing_url)
    return {
        "status": TelegramPost.Status.PENDING,
        "message_text": message_text,
        "landing_url": landing_url,
        "payload_sha256": _sha256(message_text),
        "target_fingerprint": _target_fingerprint(channel_id),
    }


def _claim_delivery(
    queue_item_id: int,
    *,
    task_id: str,
    channel_id: str,
    public_base_url: str,
) -> tuple[PublicationQueueItem, TelegramPost, TelegramDeliveryResult | None]:
    now = timezone.now()

    with transaction.atomic():
        # Lock only publication_queue itself. latest_price is nullable, so joining
        # it into SELECT ... FOR UPDATE creates an outer join that PostgreSQL
        # refuses to lock ("FOR UPDATE cannot be applied to the nullable side
        # of an outer join"). Related course/provider data can be loaded lazily
        # while this transaction still owns the queue-row lock.
        queue_item = PublicationQueueItem.objects.select_for_update().get(
            pk=queue_item_id
        )

        if queue_item.status == PublicationQueueItem.Status.SENT:
            try:
                post = queue_item.telegram_post
            except TelegramPost.DoesNotExist:
                return queue_item, TelegramPost(), _result(
                    queue_item,
                    status="already_sent",
                    detail="Queue item was already marked sent.",
                    sent=True,
                )
            return queue_item, post, _result(
                queue_item,
                status="already_sent",
                detail="Telegram post was already sent.",
                sent=True,
                telegram_message_id=post.telegram_message_id,
                attempts=post.attempts,
            )

        if queue_item.status != PublicationQueueItem.Status.QUEUED:
            try:
                post = queue_item.telegram_post
            except TelegramPost.DoesNotExist:
                post = TelegramPost()
            return queue_item, post, _result(
                queue_item,
                status="not_queued",
                detail=f"Queue item is {queue_item.status}.",
            )

        try:
            post = TelegramPost.objects.select_for_update().get(queue_item=queue_item)
        except TelegramPost.DoesNotExist:
            post = TelegramPost.objects.create(
                queue_item=queue_item,
                **_snapshot_defaults(
                    queue_item,
                    channel_id=channel_id,
                    public_base_url=public_base_url,
                ),
            )

        if post.status == TelegramPost.Status.SENT:
            queue_item.status = PublicationQueueItem.Status.SENT
            queue_item.sent_at = post.sent_at or now
            queue_item.error_message = ""
            queue_item.save(
                update_fields=("status", "sent_at", "error_message", "updated_at")
            )
            return queue_item, post, _result(
                queue_item,
                status="already_sent",
                detail="Telegram post was already sent.",
                sent=True,
                telegram_message_id=post.telegram_message_id,
                attempts=post.attempts,
            )

        if post.status == TelegramPost.Status.SENDING:
            return queue_item, post, _result(
                queue_item,
                status="busy",
                detail="Another Telegram delivery attempt is already in progress.",
                attempts=post.attempts,
            )

        if post.status == TelegramPost.Status.RETRY_WAIT:
            if post.task_id and post.task_id != task_id:
                return queue_item, post, _result(
                    queue_item,
                    status="retry_owned",
                    detail="A scheduled Telegram retry already owns this delivery.",
                    attempts=post.attempts,
                )

        if post.status == TelegramPost.Status.AMBIGUOUS:
            return queue_item, post, _result(
                queue_item,
                status="ambiguous",
                detail="Delivery outcome is ambiguous and requires manual verification.",
                attempts=post.attempts,
            )

        if post.status in (TelegramPost.Status.FAILED, TelegramPost.Status.CANCELLED):
            return queue_item, post, _result(
                queue_item,
                status=post.status,
                detail="Delivery is terminal until an administrator explicitly requeues it.",
                attempts=post.attempts,
            )

        if post.target_fingerprint != _target_fingerprint(channel_id):
            post.status = TelegramPost.Status.FAILED
            post.last_error = (
                "Configured Telegram target changed after this post was prepared. "
                "Requeue explicitly to create a new audited delivery attempt."
            )
            post.save(update_fields=("status", "last_error", "updated_at"))
            queue_item.status = PublicationQueueItem.Status.FAILED
            queue_item.error_message = post.last_error
            queue_item.save(update_fields=("status", "error_message", "updated_at"))
            return queue_item, post, _result(
                queue_item,
                status="failed",
                detail=post.last_error,
                attempts=post.attempts,
            )

        post.status = TelegramPost.Status.SENDING
        post.task_id = task_id
        post.attempts += 1
        post.last_error = ""
        post.last_attempt_at = now
        if post.first_attempt_at is None:
            post.first_attempt_at = now
        post.save(
            update_fields=(
                "status",
                "task_id",
                "attempts",
                "last_error",
                "last_attempt_at",
                "first_attempt_at",
                "updated_at",
            )
        )

        queue_item.attempts += 1
        queue_item.error_message = ""
        queue_item.save(update_fields=("attempts", "error_message", "updated_at"))

        return queue_item, post, None


def _mark_retry_wait(
    queue_item_id: int,
    *,
    task_id: str,
    message: str,
) -> None:
    with transaction.atomic():
        queue_item = PublicationQueueItem.objects.select_for_update().get(pk=queue_item_id)
        try:
            post = TelegramPost.objects.select_for_update().get(queue_item=queue_item)
        except TelegramPost.DoesNotExist:
            return

        if post.status == TelegramPost.Status.SENT:
            return
        if post.task_id and post.task_id != task_id:
            return

        post.status = TelegramPost.Status.RETRY_WAIT
        post.last_error = message
        post.save(update_fields=("status", "last_error", "updated_at"))

        if queue_item.status == PublicationQueueItem.Status.QUEUED:
            queue_item.error_message = message
            queue_item.save(update_fields=("error_message", "updated_at"))


def _mark_terminal_failure(
    queue_item_id: int,
    *,
    task_id: str,
    post_status: str,
    message: str,
) -> None:
    with transaction.atomic():
        queue_item = PublicationQueueItem.objects.select_for_update().get(pk=queue_item_id)
        try:
            post = TelegramPost.objects.select_for_update().get(queue_item=queue_item)
        except TelegramPost.DoesNotExist:
            return

        if post.status == TelegramPost.Status.SENT:
            return
        if post.task_id and post.task_id != task_id:
            return

        post.status = post_status
        post.last_error = message
        post.save(update_fields=("status", "last_error", "updated_at"))

        if queue_item.status == PublicationQueueItem.Status.QUEUED:
            queue_item.status = PublicationQueueItem.Status.FAILED
            queue_item.error_message = message
            queue_item.save(update_fields=("status", "error_message", "updated_at"))


def mark_retry_exhausted(queue_item_id: int, *, task_id: str) -> None:
    _mark_terminal_failure(
        queue_item_id,
        task_id=task_id,
        post_status=TelegramPost.Status.FAILED,
        message="Telegram rate-limit retries were exhausted.",
    )


def _mark_sent(
    queue_item_id: int,
    *,
    task_id: str,
    telegram_message_id: int,
) -> TelegramDeliveryResult:
    now = timezone.now()

    with transaction.atomic():
        queue_item = PublicationQueueItem.objects.select_for_update().get(pk=queue_item_id)
        post = TelegramPost.objects.select_for_update().get(queue_item=queue_item)

        if post.status == TelegramPost.Status.SENT:
            return _result(
                queue_item,
                status="already_sent",
                detail="Telegram post was already committed as sent.",
                sent=True,
                telegram_message_id=post.telegram_message_id,
                attempts=post.attempts,
            )

        if post.task_id and post.task_id != task_id:
            return _result(
                queue_item,
                status="ownership_changed",
                detail="Delivery ownership changed before the send result was committed.",
                attempts=post.attempts,
            )

        post.status = TelegramPost.Status.SENT
        post.telegram_message_id = telegram_message_id
        post.sent_at = now
        post.last_error = ""
        post.save(
            update_fields=(
                "status",
                "telegram_message_id",
                "sent_at",
                "last_error",
                "updated_at",
            )
        )

        queue_item.status = PublicationQueueItem.Status.SENT
        queue_item.sent_at = now
        queue_item.error_message = ""
        queue_item.save(
            update_fields=("status", "sent_at", "error_message", "updated_at")
        )

        return _result(
            queue_item,
            status="sent",
            detail="Telegram message sent.",
            sent=True,
            telegram_message_id=telegram_message_id,
            attempts=post.attempts,
        )


def attempt_telegram_delivery(
    queue_item_id: int,
    *,
    task_id: str,
    client: TelegramBotClient | None = None,
) -> TelegramDeliveryResult:
    queue_item = _load_queue_item(queue_item_id)

    if queue_item.status == PublicationQueueItem.Status.SENT:
        try:
            post = queue_item.telegram_post
        except TelegramPost.DoesNotExist:
            post = None
        return _result(
            queue_item,
            status="already_sent",
            detail="Queue item was already sent.",
            sent=True,
            telegram_message_id=post.telegram_message_id if post else None,
            attempts=post.attempts if post else queue_item.attempts,
        )

    if queue_item.status != PublicationQueueItem.Status.QUEUED:
        return _result(
            queue_item,
            status="not_queued",
            detail=f"Queue item is {queue_item.status}.",
        )

    evaluation = evaluate_course_for_publication(
        queue_item.course,
        create_queue_item=False,
    )
    if not evaluation.eligible:
        queue_item.refresh_from_db()
        return _result(
            queue_item,
            status="cancelled",
            detail="Course is no longer publication-eligible.",
        )

    config = get_telegram_config()
    if not config.enabled:
        return _result(
            queue_item,
            status="disabled",
            detail="Telegram publication is disabled.",
        )

    try:
        validate_telegram_config(config)
    except TelegramConfigurationError as exc:
        return _result(
            queue_item,
            status="configuration_error",
            detail=str(exc),
        )

    queue_item, post, early = _claim_delivery(
        queue_item_id,
        task_id=task_id,
        channel_id=config.channel_id,
        public_base_url=config.public_base_url,
    )
    if early is not None:
        return early

    client = client or TelegramBotClient(config)

    try:
        sent = client.send_message(post.message_text)
    except TelegramRateLimitError as exc:
        message = f"Telegram rate limited; retry after {exc.retry_after} second(s)."
        _mark_retry_wait(queue_item_id, task_id=task_id, message=message)
        raise
    except TelegramPermanentError as exc:
        message = str(exc)
        _mark_terminal_failure(
            queue_item_id,
            task_id=task_id,
            post_status=TelegramPost.Status.FAILED,
            message=message,
        )
        raise
    except TelegramAmbiguousError as exc:
        message = str(exc)
        _mark_terminal_failure(
            queue_item_id,
            task_id=task_id,
            post_status=TelegramPost.Status.AMBIGUOUS,
            message=message,
        )
        raise

    return _mark_sent(
        queue_item_id,
        task_id=task_id,
        telegram_message_id=sent.message_id,
    )


def get_dispatchable_queue_item_ids(
    *,
    provider_id: int | None = None,
    limit: int = 50,
) -> list[int]:
    limit = min(max(int(limit), 1), 500)
    queryset = PublicationQueueItem.objects.filter(
        status=PublicationQueueItem.Status.QUEUED,
    ).filter(
        Q(telegram_post__isnull=True)
        | Q(telegram_post__status=TelegramPost.Status.PENDING)
    )
    if provider_id is not None:
        queryset = queryset.filter(course__provider_id=provider_id)

    return list(
        queryset.order_by("queued_at", "pk").values_list("pk", flat=True)[:limit]
    )


def cancel_publication_queue_item(queue_item_id: int, *, reason: str) -> bool:
    now = timezone.now()

    with transaction.atomic():
        try:
            queue_item = PublicationQueueItem.objects.select_for_update().get(
                pk=queue_item_id
            )
        except PublicationQueueItem.DoesNotExist:
            return False

        if queue_item.status != PublicationQueueItem.Status.QUEUED:
            return False

        queue_item.status = PublicationQueueItem.Status.CANCELLED
        queue_item.error_message = reason
        queue_item.save(update_fields=("status", "error_message", "updated_at"))

        try:
            post = TelegramPost.objects.select_for_update().get(queue_item=queue_item)
        except TelegramPost.DoesNotExist:
            return True

        if post.status != TelegramPost.Status.SENT:
            post.status = TelegramPost.Status.CANCELLED
            post.last_error = reason
            post.save(update_fields=("status", "last_error", "updated_at"))

        _ = now
        return True


def requeue_failed_telegram_delivery(
    queue_item_id: int,
    *,
    allow_ambiguous: bool = False,
) -> bool:
    with transaction.atomic():
        try:
            queue_item = PublicationQueueItem.objects.select_for_update().get(
                pk=queue_item_id
            )
            post = TelegramPost.objects.select_for_update().get(queue_item=queue_item)
        except (PublicationQueueItem.DoesNotExist, TelegramPost.DoesNotExist):
            return False

        allowed = {TelegramPost.Status.FAILED}
        if allow_ambiguous:
            allowed.add(TelegramPost.Status.AMBIGUOUS)

        if queue_item.status != PublicationQueueItem.Status.FAILED:
            return False
        if post.status not in allowed:
            return False

        config = get_telegram_config()
        try:
            validate_telegram_config(config)
        except TelegramConfigurationError:
            return False
        if not config.enabled:
            return False

        # A requeue is a new audited attempt. Re-render only after an operator
        # explicitly chose to retry; this also allows a deliberate channel or
        # public-base-url change to take effect.
        defaults = _snapshot_defaults(
            queue_item,
            channel_id=config.channel_id,
            public_base_url=config.public_base_url,
        )
        post.status = TelegramPost.Status.PENDING
        post.telegram_message_id = None
        post.message_text = defaults["message_text"]
        post.landing_url = defaults["landing_url"]
        post.payload_sha256 = defaults["payload_sha256"]
        post.target_fingerprint = defaults["target_fingerprint"]
        post.task_id = ""
        post.last_error = ""
        post.sent_at = None
        post.save(
            update_fields=(
                "status",
                "telegram_message_id",
                "message_text",
                "landing_url",
                "payload_sha256",
                "target_fingerprint",
                "task_id",
                "last_error",
                "sent_at",
                "updated_at",
            )
        )

        queue_item.status = PublicationQueueItem.Status.QUEUED
        queue_item.sent_at = None
        queue_item.error_message = ""
        queue_item.save(
            update_fields=("status", "sent_at", "error_message", "updated_at")
        )
        return True


def reconcile_stale_sending_deliveries(*, now=None) -> int:
    config = get_telegram_config()
    now = now or timezone.now()
    cutoff = now - timedelta(minutes=config.stale_send_minutes)

    stale_ids = list(
        TelegramPost.objects.filter(
            status=TelegramPost.Status.SENDING,
            last_attempt_at__lt=cutoff,
        ).values_list("queue_item_id", flat=True)
    )

    updated = 0
    for queue_item_id in stale_ids:
        with transaction.atomic():
            try:
                queue_item = PublicationQueueItem.objects.select_for_update().get(
                    pk=queue_item_id
                )
                post = TelegramPost.objects.select_for_update().get(queue_item=queue_item)
            except (PublicationQueueItem.DoesNotExist, TelegramPost.DoesNotExist):
                continue

            if post.status != TelegramPost.Status.SENDING:
                continue
            if post.last_attempt_at is None or post.last_attempt_at >= cutoff:
                continue

            message = (
                "Telegram worker stopped during an in-flight send. Delivery outcome is "
                "ambiguous; verify the channel before requeueing."
            )
            post.status = TelegramPost.Status.AMBIGUOUS
            post.last_error = message
            post.save(update_fields=("status", "last_error", "updated_at"))

            if queue_item.status == PublicationQueueItem.Status.QUEUED:
                queue_item.status = PublicationQueueItem.Status.FAILED
                queue_item.error_message = message
                queue_item.save(update_fields=("status", "error_message", "updated_at"))
            updated += 1

    return updated