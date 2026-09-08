from __future__ import annotations

from django.db import models
from django.db.models import Q
from django.utils import timezone

from courses.models import Course

from .validators import validate_https_destination


class AffiliateLink(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="affiliate_links",
    )
    url = models.TextField(validators=[validate_https_destination])
    network = models.CharField(max_length=120, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INACTIVE,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "affiliate_links"
        constraints = [
            models.UniqueConstraint(
                fields=("course",),
                condition=Q(status="active"),
                name="affiliate_one_active_course",
            ),
        ]
        indexes = [
            models.Index(
                fields=("status", "updated_at"),
                name="affiliate_status_updated_idx",
            ),
        ]
        ordering = ("course__title", "id")

    def __str__(self) -> str:
        label = self.network.strip() or "Affiliate"
        return f"{self.course}: {label} ({self.get_status_display()})"


class ClickEvent(models.Model):
    class DestinationKind(models.TextChoices):
        PROVIDER = "provider", "Provider"
        AFFILIATE = "affiliate", "Affiliate"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="click_events",
    )
    affiliate_link = models.ForeignKey(
        AffiliateLink,
        on_delete=models.SET_NULL,
        related_name="click_events",
        null=True,
        blank=True,
    )
    destination_kind = models.CharField(
        max_length=20,
        choices=DestinationKind.choices,
    )
    source = models.CharField(max_length=50, default="course_page")
    campaign = models.CharField(max_length=100, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "click_events"
        indexes = [
            models.Index(
                fields=("course", "occurred_at"),
                name="click_course_time_idx",
            ),
            models.Index(
                fields=("source", "occurred_at"),
                name="click_source_time_idx",
            ),
        ]
        ordering = ("-occurred_at", "-id")

    def __str__(self) -> str:
        return f"{self.course}: {self.source} at {self.occurred_at:%Y-%m-%d %H:%M:%S}"
