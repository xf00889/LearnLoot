from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from courses.models import Course
from pricing.models import CoursePrice


class AdminOverride(models.Model):
    class Decision(models.TextChoices):
        AUTO = "auto", "Automatic rules"
        FORCE_ELIGIBLE = "force_eligible", "Force eligible"
        FORCE_INELIGIBLE = "force_ineligible", "Force ineligible"

    course = models.OneToOneField(
        Course,
        on_delete=models.CASCADE,
        related_name="publication_override",
    )
    decision = models.CharField(
        max_length=30,
        choices=Decision.choices,
        default=Decision.AUTO,
    )
    note = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="learnloot_publication_overrides",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "admin_overrides"
        ordering = ("course__title", "id")

    def __str__(self) -> str:
        return f"{self.course}: {self.get_decision_display()}"


class DealEligibility(models.Model):
    course = models.OneToOneField(
        Course,
        on_delete=models.CASCADE,
        related_name="publication_eligibility",
    )
    latest_price = models.ForeignKey(
        CoursePrice,
        on_delete=models.SET_NULL,
        related_name="eligibility_snapshots",
        null=True,
        blank=True,
    )
    score = models.PositiveSmallIntegerField(default=0)
    eligible = models.BooleanField(default=False)
    override_applied = models.BooleanField(default=False)
    reasons = models.JSONField(default=list)
    evaluated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "deal_eligibility"
        indexes = [
            models.Index(
                fields=("eligible", "score"),
                name="deal_eligibility_score_idx",
            ),
            models.Index(
                fields=("evaluated_at",),
                name="deal_eligibility_eval_idx",
            ),
        ]
        ordering = ("-evaluated_at", "id")

    def __str__(self) -> str:
        state = "Eligible" if self.eligible else "Ineligible"
        return f"{self.course}: {state} ({self.score})"


class PublicationQueueItem(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="publication_queue_items",
    )
    latest_price = models.ForeignKey(
        CoursePrice,
        on_delete=models.SET_NULL,
        related_name="publication_queue_items",
        null=True,
        blank=True,
    )
    score = models.PositiveSmallIntegerField(default=0)
    override_applied = models.BooleanField(default=False)
    reasons = models.JSONField(default=list)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    queued_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "publication_queue"
        constraints = [
            models.UniqueConstraint(
                fields=("course",),
                condition=Q(status="queued"),
                name="publication_one_queued_course",
            ),
        ]
        indexes = [
            models.Index(
                fields=("status", "queued_at"),
                name="publication_status_time_idx",
            ),
            models.Index(
                fields=("course", "status"),
                name="publication_course_status_idx",
            ),
        ]
        ordering = ("-queued_at", "id")

    def __str__(self) -> str:
        return f"{self.course}: {self.get_status_display()}"


class TelegramPost(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENDING = "sending", "Sending"
        RETRY_WAIT = "retry_wait", "Waiting to retry"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        AMBIGUOUS = "ambiguous", "Ambiguous outcome"
        CANCELLED = "cancelled", "Cancelled"

    queue_item = models.OneToOneField(
        PublicationQueueItem,
        on_delete=models.CASCADE,
        related_name="telegram_post",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    message_text = models.TextField()
    landing_url = models.TextField()
    payload_sha256 = models.CharField(max_length=64)
    target_fingerprint = models.CharField(max_length=64)
    task_id = models.CharField(max_length=255, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    first_attempt_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "telegram_posts"
        indexes = [
            models.Index(
                fields=("status", "last_attempt_at"),
                name="telegram_status_attempt_idx",
            ),
            models.Index(
                fields=("sent_at",),
                name="telegram_sent_at_idx",
            ),
        ]
        ordering = ("-created_at", "id")

    def __str__(self) -> str:
        return f"Telegram {self.get_status_display()}: {self.queue_item.course}"