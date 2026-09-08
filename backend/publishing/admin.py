from django.contrib import admin, messages

from .delivery import (
    cancel_publication_queue_item,
    requeue_failed_telegram_delivery,
)
from .models import AdminOverride, DealEligibility, PublicationQueueItem, TelegramPost
from .services import evaluate_course_for_publication
from .tasks import publish_telegram_queue_item
from .telegram import telegram_publication_enabled


@admin.register(AdminOverride)
class AdminOverrideAdmin(admin.ModelAdmin):
    list_display = ("course", "decision", "updated_by", "updated_at")
    list_filter = ("decision",)
    search_fields = (
        "course__title",
        "course__external_id",
        "note",
        "updated_by__username",
    )
    autocomplete_fields = ("course",)
    readonly_fields = ("updated_by", "created_at", "updated_at")
    list_select_related = ("course", "updated_by")

    def save_model(self, request, obj, form, change):
        user = getattr(request, "user", None)
        obj.updated_by = user if getattr(user, "is_authenticated", False) else None
        super().save_model(request, obj, form, change)

        # Override evaluation is lightweight database work only. It does not
        # run Scrapy/Playwright or make provider requests inside the admin HTTP
        # request, and it guarantees force-ineligible changes cancel queued
        # publication immediately.
        evaluate_course_for_publication(obj.course)


@admin.register(DealEligibility)
class DealEligibilityAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "eligible",
        "score",
        "override_applied",
        "latest_price",
        "evaluated_at",
    )
    list_filter = ("eligible", "override_applied")
    search_fields = ("course__title", "course__external_id")
    readonly_fields = (
        "course",
        "latest_price",
        "score",
        "eligible",
        "override_applied",
        "reasons",
        "evaluated_at",
    )
    list_select_related = ("course", "latest_price")
    date_hierarchy = "evaluated_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PublicationQueueItem)
class PublicationQueueItemAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "status",
        "telegram_status",
        "score",
        "override_applied",
        "queued_at",
        "sent_at",
        "attempts",
    )
    list_filter = ("status", "override_applied")
    search_fields = (
        "course__title",
        "course__external_id",
        "error_message",
        "telegram_post__last_error",
    )
    readonly_fields = (
        "course",
        "latest_price",
        "score",
        "override_applied",
        "reasons",
        "status",
        "queued_at",
        "sent_at",
        "attempts",
        "error_message",
        "updated_at",
        "telegram_status",
        "telegram_message_id",
    )
    list_select_related = ("course", "latest_price")
    date_hierarchy = "queued_at"
    actions = (
        "publish_selected_queued_items",
        "retry_known_failed_telegram_items",
        "requeue_ambiguous_after_manual_verification",
        "cancel_queued_items",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Telegram status")
    def telegram_status(self, obj):
        try:
            return obj.telegram_post.get_status_display()
        except TelegramPost.DoesNotExist:
            return "Not prepared"

    @admin.display(description="Telegram message id")
    def telegram_message_id(self, obj):
        try:
            return obj.telegram_post.telegram_message_id or "â€”"
        except TelegramPost.DoesNotExist:
            return "â€”"

    @admin.action(
        description="Publish selected queued items to Telegram",
        permissions=["change"],
    )
    def publish_selected_queued_items(self, request, queryset):
        if not telegram_publication_enabled():
            self.message_user(
                request,
                "Telegram publication is disabled. No tasks were queued.",
                level=messages.WARNING,
            )
            return

        queued = list(
            queryset.filter(
                status=PublicationQueueItem.Status.QUEUED
            ).values_list("pk", flat=True)
        )
        for queue_item_id in queued:
            publish_telegram_queue_item.delay(queue_item_id)

        self.message_user(
            request,
            f"Queued {len(queued)} Telegram publication task(s).",
            level=messages.SUCCESS,
        )

    @admin.action(
        description="Retry selected known-failed Telegram deliveries",
        permissions=["change"],
    )
    def retry_known_failed_telegram_items(self, request, queryset):
        retried = 0
        for queue_item_id in queryset.values_list("pk", flat=True):
            if requeue_failed_telegram_delivery(
                queue_item_id,
                allow_ambiguous=False,
            ):
                publish_telegram_queue_item.delay(queue_item_id)
                retried += 1

        self.message_user(
            request,
            f"Requeued {retried} known-failed Telegram delivery item(s).",
            level=messages.SUCCESS if retried else messages.WARNING,
        )

    @admin.action(
        description=(
            "Requeue selected ambiguous Telegram deliveries AFTER manual "
            "channel verification"
        ),
        permissions=["change"],
    )
    def requeue_ambiguous_after_manual_verification(self, request, queryset):
        retried = 0
        for queue_item_id in queryset.values_list("pk", flat=True):
            if requeue_failed_telegram_delivery(
                queue_item_id,
                allow_ambiguous=True,
            ):
                publish_telegram_queue_item.delay(queue_item_id)
                retried += 1

        self.message_user(
            request,
            (
                f"Requeued {retried} ambiguous/failed Telegram delivery item(s). "
                "This action assumes the channel was manually checked first."
            ),
            level=messages.WARNING if retried else messages.INFO,
        )

    @admin.action(description="Cancel selected queued items", permissions=["change"])
    def cancel_queued_items(self, request, queryset):
        cancelled = 0
        for queue_item_id in queryset.values_list("pk", flat=True):
            if cancel_publication_queue_item(
                queue_item_id,
                reason="Cancelled by admin",
            ):
                cancelled += 1

        self.message_user(
            request,
            f"Cancelled {cancelled} queued publication item(s).",
            level=messages.SUCCESS,
        )


@admin.register(TelegramPost)
class TelegramPostAdmin(admin.ModelAdmin):
    list_display = (
        "queue_item",
        "status",
        "telegram_message_id",
        "attempts",
        "last_attempt_at",
        "sent_at",
    )
    list_filter = ("status",)
    search_fields = (
        "queue_item__course__title",
        "queue_item__course__external_id",
        "telegram_message_id",
        "last_error",
    )
    readonly_fields = (
        "queue_item",
        "status",
        "telegram_message_id",
        "message_text",
        "landing_url",
        "payload_sha256",
        "target_fingerprint",
        "task_id",
        "attempts",
        "last_error",
        "first_attempt_at",
        "last_attempt_at",
        "sent_at",
        "created_at",
        "updated_at",
    )
    list_select_related = ("queue_item__course",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False