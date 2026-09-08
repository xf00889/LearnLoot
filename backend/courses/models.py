from django.db import models
from django.utils import timezone

from providers.models import Provider


class Course(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        HIDDEN = "hidden", "Hidden"
        ARCHIVED = "archived", "Archived"

    provider = models.ForeignKey(
        Provider,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    external_id = models.CharField(max_length=100)
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=600, db_index=False)
    canonical_url = models.TextField()
    thumbnail_url = models.TextField(blank=True)
    instructor_name = models.CharField(max_length=255, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    review_count = models.PositiveIntegerField(null=True, blank=True)
    student_count = models.PositiveIntegerField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "courses"
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "external_id"),
                name="course_provider_external_uniq",
            ),
            models.UniqueConstraint(
                fields=("provider", "slug"),
                name="course_provider_slug_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=("provider", "status"),
                name="courses_provider_status_idx",
            ),
            models.Index(
                fields=("last_checked_at",),
                name="courses_last_checked_idx",
            ),
        ]
        ordering = ("-last_seen_at", "id")

    def __str__(self) -> str:
        return self.title


class CourseSource(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="sources",
    )
    source_url = models.TextField()
    source_type = models.CharField(max_length=50)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "course_sources"
        indexes = [
            models.Index(
                fields=("course", "last_seen_at"),
                name="course_sources_seen_idx",
            ),
        ]
        ordering = ("-last_seen_at", "id")

    def __str__(self) -> str:
        return f"{self.course} ({self.source_type})"