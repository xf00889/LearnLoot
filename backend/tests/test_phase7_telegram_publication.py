from datetime import timedelta
from decimal import Decimal
import io
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

import pytest
from django.contrib import admin
from django.test import RequestFactory, override_settings
from django.utils import timezone

from courses.models import Course
from pricing.models import CoursePrice
from providers.models import Provider
from publishing.admin import PublicationQueueItemAdmin, TelegramPostAdmin
from publishing.delivery import (
    attempt_telegram_delivery,
    get_dispatchable_queue_item_ids,
    reconcile_stale_sending_deliveries,
    requeue_failed_telegram_delivery,
)
from publishing.models import PublicationQueueItem, TelegramPost
from publishing.services import evaluate_course_for_publication
from publishing.tasks import (
    dispatch_queued_telegram_publications,
    evaluate_course_publication_candidate,
    evaluate_provider_publication_candidates,
    publish_telegram_queue_item,
    reconcile_stale_telegram_delivery_tasks,
)
from publishing.telegram import (
    TelegramAmbiguousError,
    TelegramBotClient,
    TelegramConfig,
    TelegramPermanentError,
    TelegramRateLimitError,
    TelegramSendResult,
    build_course_landing_url,
    render_telegram_course_message,
)


TELEGRAM_SETTINGS = {
    "LEARNLOOT_TELEGRAM_ENABLED": True,
    "LEARNLOOT_TELEGRAM_BOT_TOKEN": "test-token-never-real",
    "LEARNLOOT_TELEGRAM_CHAT_ID": "@learnloot_test",
    "LEARNLOOT_TELEGRAM_API_BASE_URL": "https://api.telegram.org",
    "LEARNLOOT_TELEGRAM_TIMEOUT_SECONDS": 5.0,
    "LEARNLOOT_TELEGRAM_MAX_RETRIES": 3,
    "LEARNLOOT_TELEGRAM_RETRY_BASE_SECONDS": 30,
    "LEARNLOOT_TELEGRAM_STALE_SEND_MINUTES": 15,
    "LEARNLOOT_PUBLIC_BASE_URL": "https://learnloot.example",
}


@pytest.fixture
def provider(db):
    return Provider.objects.create(name="Udemy & Courses", slug="udemy")


@pytest.fixture
def free_course(provider):
    now = timezone.now()
    course = Course.objects.create(
        provider=provider,
        external_id="slug:telegram-course",
        title='Python <Fast> & "Safe"',
        slug="python-fast-safe",
        canonical_url="https://www.udemy.com/course/python-fast-safe/",
        thumbnail_url="https://img.example/course.jpg",
        instructor_name="Alice & Bob",
        rating=Decimal("4.70"),
        review_count=12_345,
        student_count=55_000,
        duration_minutes=125,
        description="A complete free course.",
        last_checked_at=now,
        last_seen_at=now,
    )
    CoursePrice.objects.create(
        course=course,
        amount=Decimal("0.00"),
        currency="USD",
        is_free=True,
        price_type="free",
        observed_at=now,
        source_url=course.canonical_url,
    )
    return course


@pytest.fixture
def queued_item(free_course):
    result = evaluate_course_for_publication(free_course)
    assert result.queue_created is True
    return PublicationQueueItem.objects.get(pk=result.queue_item_id)


class FakeResponse:
    def __init__(self, payload: dict):
        self.raw = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        return self.raw if size < 0 else self.raw[:size]


class SuccessfulClient:
    def __init__(self, message_id=9001):
        self.message_id = message_id
        self.messages = []

    def send_message(self, text):
        self.messages.append(text)
        return TelegramSendResult(message_id=self.message_id)


class PermanentFailureClient:
    def send_message(self, text):
        raise TelegramPermanentError("Telegram rejected the message: bad request")


class AmbiguousFailureClient:
    def send_message(self, text):
        raise TelegramAmbiguousError("Telegram network failure with ambiguous delivery outcome")


class RateLimitedClient:
    def send_message(self, text):
        raise TelegramRateLimitError("Telegram rate limit", retry_after=17)


def telegram_config():
    return TelegramConfig(
        enabled=True,
        bot_token="secret-test-token",
        chat_id="@test_channel",
        api_base_url="https://api.telegram.org",
        timeout_seconds=5.0,
        max_retries=3,
        retry_base_seconds=30,
        stale_send_minutes=15,
        public_base_url="https://learnloot.example",
    )


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_renderer_escapes_html_and_links_to_learnloot_not_provider(free_course):
    landing_url = build_course_landing_url(free_course)
    message = render_telegram_course_message(free_course, landing_url=landing_url)

    assert "Python &lt;Fast&gt; &amp; &quot;Safe&quot;" in message
    assert "Alice &amp; Bob" in message
    assert "12,345 reviews" in message
    assert "2h 5m" in message
    assert "https://learnloot.example/courses/udemy/python-fast-safe" in message
    assert free_course.canonical_url not in message
    assert len(message) <= 4096


def test_bot_client_posts_send_message_and_parses_message_id():
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = parse_qs(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "ok": True,
                "result": {
                    "message_id": 321,
                },
            }
        )

    config = telegram_config()
    client = TelegramBotClient(config, opener=opener)
    result = client.send_message("<b>Free course</b>")

    assert result.message_id == 321
    assert captured["url"].endswith("/botsecret-test-token/sendMessage")
    assert captured["body"]["chat_id"] == ["@test_channel"]
    assert captured["body"]["parse_mode"] == ["HTML"]
    assert captured["timeout"] == 5.0


def test_bot_client_uses_retry_after_for_explicit_flood_control():
    payload = {
        "ok": False,
        "error_code": 429,
        "description": "Too Many Requests",
        "parameters": {"retry_after": 23},
    }

    def opener(request, timeout):
        raise HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(json.dumps(payload).encode("utf-8")),
        )

    client = TelegramBotClient(telegram_config(), opener=opener)

    with pytest.raises(TelegramRateLimitError) as exc:
        client.send_message("Free course")

    assert exc.value.retry_after == 23


def test_bot_client_never_leaks_token_or_chat_id_in_network_error():
    config = telegram_config()

    def opener(request, timeout):
        raise URLError(
            f"failure for {config.bot_token} and {config.chat_id}"
        )

    client = TelegramBotClient(config, opener=opener)

    with pytest.raises(TelegramAmbiguousError) as exc:
        client.send_message("Free course")

    message = str(exc.value)
    assert config.bot_token not in message
    assert config.chat_id not in message
    assert "[REDACTED_TOKEN]" in message
    assert "[REDACTED_CHAT]" in message


@pytest.mark.django_db
@override_settings(
    **{
        **TELEGRAM_SETTINGS,
        "LEARNLOOT_TELEGRAM_ENABLED": False,
    }
)
def test_disabled_delivery_leaves_queue_untouched(queued_item):
    client = SuccessfulClient()

    result = attempt_telegram_delivery(
        queued_item.pk,
        task_id="task-disabled",
        client=client,
    )

    queued_item.refresh_from_db()
    assert result.status == "disabled"
    assert queued_item.status == PublicationQueueItem.Status.QUEUED
    assert queued_item.attempts == 0
    assert TelegramPost.objects.filter(queue_item=queued_item).exists() is False
    assert client.messages == []


@pytest.mark.django_db
@override_settings(
    **{
        **TELEGRAM_SETTINGS,
        "LEARNLOOT_TELEGRAM_BOT_TOKEN": "",
    }
)
def test_missing_credentials_leave_queue_available_for_later_configuration(queued_item):
    result = attempt_telegram_delivery(
        queued_item.pk,
        task_id="task-no-config",
        client=SuccessfulClient(),
    )

    queued_item.refresh_from_db()
    assert result.status == "configuration_error"
    assert queued_item.status == PublicationQueueItem.Status.QUEUED
    assert queued_item.attempts == 0


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_successful_delivery_is_persisted_and_application_idempotent(queued_item):
    client = SuccessfulClient(message_id=444)

    first = attempt_telegram_delivery(
        queued_item.pk,
        task_id="task-success",
        client=client,
    )
    second = attempt_telegram_delivery(
        queued_item.pk,
        task_id="task-duplicate",
        client=client,
    )

    queued_item.refresh_from_db()
    post = TelegramPost.objects.get(queue_item=queued_item)

    assert first.status == "sent"
    assert first.telegram_message_id == 444
    assert second.status == "already_sent"
    assert len(client.messages) == 1
    assert queued_item.status == PublicationQueueItem.Status.SENT
    assert queued_item.sent_at is not None
    assert queued_item.attempts == 1
    assert post.status == TelegramPost.Status.SENT
    assert post.telegram_message_id == 444
    assert post.attempts == 1
    assert post.payload_sha256
    assert len(post.payload_sha256) == 64
    assert len(post.target_fingerprint) == 64
    assert "@learnloot_test" not in post.target_fingerprint
    assert "test-token-never-real" not in post.message_text


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_paid_change_is_revalidated_and_cancelled_before_telegram(queued_item):
    now = timezone.now()
    CoursePrice.objects.create(
        course=queued_item.course,
        amount=Decimal("19.99"),
        currency="USD",
        is_free=False,
        price_type="paid",
        observed_at=now,
        source_url=queued_item.course.canonical_url,
    )
    queued_item.course.last_checked_at = now
    queued_item.course.save(update_fields=("last_checked_at",))
    client = SuccessfulClient()

    result = attempt_telegram_delivery(
        queued_item.pk,
        task_id="task-paid",
        client=client,
    )

    queued_item.refresh_from_db()
    assert result.status == "cancelled"
    assert queued_item.status == PublicationQueueItem.Status.CANCELLED
    assert "price_not_free" in queued_item.error_message
    assert client.messages == []


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_permanent_failure_records_known_failed_state(queued_item):
    with pytest.raises(TelegramPermanentError):
        attempt_telegram_delivery(
            queued_item.pk,
            task_id="task-permanent",
            client=PermanentFailureClient(),
        )

    queued_item.refresh_from_db()
    post = TelegramPost.objects.get(queue_item=queued_item)

    assert queued_item.status == PublicationQueueItem.Status.FAILED
    assert post.status == TelegramPost.Status.FAILED
    assert queued_item.attempts == 1
    assert post.attempts == 1
    assert "bad request" in post.last_error


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_ambiguous_network_failure_halts_automatic_retry(queued_item):
    with pytest.raises(TelegramAmbiguousError):
        attempt_telegram_delivery(
            queued_item.pk,
            task_id="task-ambiguous",
            client=AmbiguousFailureClient(),
        )

    queued_item.refresh_from_db()
    post = TelegramPost.objects.get(queue_item=queued_item)

    assert queued_item.status == PublicationQueueItem.Status.FAILED
    assert post.status == TelegramPost.Status.AMBIGUOUS
    assert "ambiguous" in post.last_error.lower()


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_explicit_rate_limit_stays_queued_for_owned_retry(queued_item):
    with pytest.raises(TelegramRateLimitError) as exc:
        attempt_telegram_delivery(
            queued_item.pk,
            task_id="task-rate-limit",
            client=RateLimitedClient(),
        )

    assert exc.value.retry_after == 17
    queued_item.refresh_from_db()
    post = TelegramPost.objects.get(queue_item=queued_item)

    assert queued_item.status == PublicationQueueItem.Status.QUEUED
    assert post.status == TelegramPost.Status.RETRY_WAIT
    assert post.task_id == "task-rate-limit"
    assert queued_item.attempts == 1


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_rate_limit_retry_same_task_can_resume_without_new_snapshot(queued_item):
    with pytest.raises(TelegramRateLimitError):
        attempt_telegram_delivery(
            queued_item.pk,
            task_id="task-rate-resume",
            client=RateLimitedClient(),
        )

    post = TelegramPost.objects.get(queue_item=queued_item)
    original_payload_hash = post.payload_sha256

    result = attempt_telegram_delivery(
        queued_item.pk,
        task_id="task-rate-resume",
        client=SuccessfulClient(message_id=555),
    )

    post.refresh_from_db()
    assert result.status == "sent"
    assert post.status == TelegramPost.Status.SENT
    assert post.attempts == 2
    assert post.payload_sha256 == original_payload_hash


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_different_task_does_not_steal_scheduled_retry(queued_item):
    with pytest.raises(TelegramRateLimitError):
        attempt_telegram_delivery(
            queued_item.pk,
            task_id="owner-task",
            client=RateLimitedClient(),
        )

    client = SuccessfulClient()
    result = attempt_telegram_delivery(
        queued_item.pk,
        task_id="other-task",
        client=client,
    )

    assert result.status == "retry_owned"
    assert client.messages == []


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_stale_sending_is_marked_ambiguous_not_resent(queued_item):
    now = timezone.now()
    TelegramPost.objects.create(
        queue_item=queued_item,
        status=TelegramPost.Status.SENDING,
        message_text="prepared",
        landing_url="https://learnloot.example/courses/udemy/python-fast-safe",
        payload_sha256="a" * 64,
        target_fingerprint="b" * 64,
        task_id="lost-task",
        attempts=1,
        first_attempt_at=now - timedelta(minutes=30),
        last_attempt_at=now - timedelta(minutes=30),
    )

    updated = reconcile_stale_sending_deliveries(now=now)

    queued_item.refresh_from_db()
    post = TelegramPost.objects.get(queue_item=queued_item)
    assert updated == 1
    assert queued_item.status == PublicationQueueItem.Status.FAILED
    assert post.status == TelegramPost.Status.AMBIGUOUS


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_known_failure_can_be_requeued_but_ambiguous_requires_explicit_flag(queued_item):
    post = TelegramPost.objects.create(
        queue_item=queued_item,
        status=TelegramPost.Status.AMBIGUOUS,
        message_text="prepared",
        landing_url="https://learnloot.example/courses/udemy/python-fast-safe",
        payload_sha256="a" * 64,
        target_fingerprint="b" * 64,
        attempts=1,
        last_error="unknown outcome",
    )
    queued_item.status = PublicationQueueItem.Status.FAILED
    queued_item.error_message = "unknown outcome"
    queued_item.save(update_fields=("status", "error_message"))

    assert requeue_failed_telegram_delivery(
        queued_item.pk,
        allow_ambiguous=False,
    ) is False

    assert requeue_failed_telegram_delivery(
        queued_item.pk,
        allow_ambiguous=True,
    ) is True

    queued_item.refresh_from_db()
    post.refresh_from_db()
    assert queued_item.status == PublicationQueueItem.Status.QUEUED
    assert post.status == TelegramPost.Status.PENDING
    assert post.task_id == ""


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_failed_or_ambiguous_delivery_blocks_fresh_queue_creation(queued_item):
    TelegramPost.objects.create(
        queue_item=queued_item,
        status=TelegramPost.Status.AMBIGUOUS,
        message_text="prepared",
        landing_url="https://learnloot.example/courses/udemy/python-fast-safe",
        payload_sha256="e" * 64,
        target_fingerprint="f" * 64,
        attempts=1,
        last_error="unknown outcome",
    )
    queued_item.status = PublicationQueueItem.Status.FAILED
    queued_item.error_message = "unknown outcome"
    queued_item.save(update_fields=("status", "error_message"))

    result = evaluate_course_for_publication(queued_item.course)

    assert result.eligible is True
    assert result.queue_created is False
    assert result.queue_item_id == queued_item.pk
    assert PublicationQueueItem.objects.filter(course=queued_item.course).count() == 1


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_dispatch_selection_excludes_terminal_or_owned_delivery_states(queued_item, provider):
    second_course = Course.objects.create(
        provider=provider,
        external_id="slug:second",
        title="Second Course",
        slug="second-course",
        canonical_url="https://www.udemy.com/course/second/",
        rating=Decimal("4.80"),
        review_count=2_000,
        last_checked_at=timezone.now(),
    )
    second_price = CoursePrice.objects.create(
        course=second_course,
        amount=Decimal("0.00"),
        currency="USD",
        is_free=True,
        price_type="free",
        observed_at=timezone.now(),
    )
    second_queue = PublicationQueueItem.objects.create(
        course=second_course,
        latest_price=second_price,
        score=90,
    )
    TelegramPost.objects.create(
        queue_item=second_queue,
        status=TelegramPost.Status.RETRY_WAIT,
        message_text="prepared",
        landing_url="https://learnloot.example/courses/udemy/second-course",
        payload_sha256="c" * 64,
        target_fingerprint="d" * 64,
        task_id="retry-owner",
    )

    ids = get_dispatchable_queue_item_ids(provider_id=provider.pk)

    assert queued_item.pk in ids
    assert second_queue.pk not in ids


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_course_evaluation_task_dispatches_new_queue_only_when_enabled(free_course):
    with patch(
        "publishing.tasks.publish_telegram_queue_item.delay"
    ) as delivery_delay:
        result = evaluate_course_publication_candidate.run(free_course.pk)

    assert result["queue_created"] is True
    delivery_delay.assert_called_once_with(result["queue_item_id"])


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_provider_evaluation_task_enqueues_dispatch(provider, free_course):
    with patch(
        "publishing.tasks.dispatch_queued_telegram_publications.delay"
    ) as dispatch_delay:
        result = evaluate_provider_publication_candidates.run(provider.pk)

    assert result["queued"] == 1
    dispatch_delay.assert_called_once_with(provider.pk)


@pytest.mark.django_db
@override_settings(**TELEGRAM_SETTINGS)
def test_dispatch_task_queues_only_selected_items(queued_item):
    with patch(
        "publishing.tasks.publish_telegram_queue_item.delay"
    ) as delivery_delay:
        result = dispatch_queued_telegram_publications.run(
            provider_id=queued_item.course.provider_id,
            limit=10,
        )

    assert result == {"status": "queued", "dispatched": 1}
    delivery_delay.assert_called_once_with(queued_item.pk)


def test_phase7_celery_tasks_are_registered():
    from config.celery import app
    import publishing.tasks  # noqa: F401

    expected = {
        "publishing.publish_telegram_queue_item",
        "publishing.dispatch_queued_telegram_publications",
        "publishing.reconcile_stale_telegram_deliveries",
        "publishing.evaluate_provider_publication_candidates",
        "publishing.evaluate_course_publication_candidate",
    }
    assert expected.issubset(set(app.tasks))


def test_phase7_admin_keeps_delivery_records_read_only():
    queue_admin = PublicationQueueItemAdmin(PublicationQueueItem, admin.site)
    post_admin = TelegramPostAdmin(TelegramPost, admin.site)
    request = RequestFactory().get("/")

    assert queue_admin.has_add_permission(request) is False
    assert queue_admin.has_delete_permission(request) is False
    assert post_admin.has_add_permission(request) is False
    assert post_admin.has_delete_permission(request) is False
    assert PublicationQueueItemAdmin.cancel_queued_items.allowed_permissions == ["change"]
    assert (
        PublicationQueueItemAdmin.publish_selected_queued_items.allowed_permissions
        == ["change"]
    )