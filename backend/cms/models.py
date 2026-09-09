from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "avif")


class MediaAsset(models.Model):
    file = models.FileField(
        upload_to="cms/media/%Y/%m/",
        validators=[FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)],
    )
    title = models.CharField(max_length=200, blank=True)
    alt_text = models.CharField(max_length=300, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="learnloot_media_assets",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cms_media_assets"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.title or self.file.name


class ContentCategory(models.Model):
    class Scope(models.TextChoices):
        COURSE = "course", "Courses"
        AFFILIATE = "affiliate", "Affiliate"

    scope = models.CharField(max_length=20, choices=Scope.choices)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    description = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cms_categories"
        constraints = [
            models.UniqueConstraint(fields=("scope", "slug"), name="cms_category_scope_slug_uniq"),
        ]
        indexes = [
            models.Index(fields=("scope", "is_active", "name"), name="cms_category_scope_active_idx"),
        ]
        ordering = ("scope", "name", "id")

    def __str__(self) -> str:
        return f"{self.get_scope_display()}: {self.name}"
