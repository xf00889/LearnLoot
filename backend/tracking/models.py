from __future__ import annotations

from django.db import models
from django.utils import timezone

from courses.models import Course


class ClickEvent(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="click_events",
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
