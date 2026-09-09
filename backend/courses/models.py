from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from providers.models import Provider


IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "avif")


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

    # CMS/editorial overrides. Discovery keeps refreshing the scraped fields
    # above while these operator-controlled values remain untouched.
    editorial_title = models.CharField(max_length=500, blank=True)
    editorial_description = models.TextField(blank=True)
    editorial_image = models.FileField(
        upload_to="courses/editorial/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)],
    )
    seo_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)
    social_image = models.FileField(
        upload_to="courses/social/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)],
    )

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

    @property
    def public_title(self) -> str:
        return self.editorial_title.strip() or self.title

    @property
    def public_description(self) -> str:
        return self.editorial_description.strip() or self.description

    @property
    def public_seo_title(self) -> str:
        return self.seo_title.strip() or self.public_title

    @property
    def public_meta_description(self) -> str:
        value = self.meta_description.strip() or self.public_description
        return value[:320]

    @property
    def is_editorially_customized(self) -> bool:
        return any(
            (
                self.editorial_title.strip(),
                self.editorial_description.strip(),
                bool(self.editorial_image),
                self.seo_title.strip(),
                self.meta_description.strip(),
                self.meta_keywords.strip(),
                bool(self.social_image),
            )
        )

    def __str__(self) -> str:
        return self.public_title


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
