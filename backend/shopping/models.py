from __future__ import annotations

from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from .validators import validate_https_affiliate_url


IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "avif")


class ShoppingPost(models.Model):
    class PostType(models.TextChoices):
        TOP_LIST = "top_10", "Top 10 / ranked list"
        FLASH_DEALS = "flash_deals", "Flash deals"
        BUYING_GUIDE = "buying_guide", "Buying guide"
        ROUNDUP = "roundup", "Product roundup"
        ARTICLE = "article", "Article"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    post_type = models.CharField(max_length=30, choices=PostType.choices, default=PostType.TOP_LIST)
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True)
    excerpt = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)
    cover_image = models.FileField(
        upload_to="shopping/posts/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)],
    )
    seo_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shopping_posts"
        indexes = [
            models.Index(fields=("status", "-published_at"), name="shop_post_status_pub_idx"),
            models.Index(fields=("post_type", "status"), name="shop_post_type_status_idx"),
        ]
        ordering = ("-published_at", "-updated_at", "id")

    @property
    def public_seo_title(self) -> str:
        return self.seo_title.strip() or self.title

    @property
    def public_meta_description(self) -> str:
        return (self.meta_description.strip() or self.excerpt.strip() or self.title)[:320]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:320]
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class ShoppingProduct(models.Model):
    post = models.ForeignKey(ShoppingPost, on_delete=models.CASCADE, related_name="products")
    position = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=220)
    image = models.FileField(
        upload_to="shopping/products/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)],
    )
    short_description = models.TextField(blank=True)
    affiliate_url = models.URLField(max_length=2000, validators=[validate_https_affiliate_url])
    displayed_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    original_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="PHP")
    badge = models.CharField(max_length=100, blank=True)
    pros = models.TextField(blank=True)
    cons = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shopping_products"
        constraints = [
            models.UniqueConstraint(fields=("post", "position"), name="shop_product_post_position_uniq"),
            models.UniqueConstraint(fields=("post", "slug"), name="shop_product_post_slug_uniq"),
        ]
        indexes = [
            models.Index(fields=("post", "is_active", "position"), name="shop_product_active_pos_idx"),
            models.Index(fields=("expires_at",), name="shop_product_expiry_idx"),
        ]
        ordering = ("position", "id")

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        self.currency = (self.currency or "PHP").strip().upper()[:3]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.position}. {self.name}"


class ShoppingClickEvent(models.Model):
    product = models.ForeignKey(ShoppingProduct, on_delete=models.PROTECT, related_name="click_events")
    source = models.CharField(max_length=50, default="shopping_page")
    campaign = models.CharField(max_length=100, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "shopping_click_events"
        indexes = [
            models.Index(fields=("product", "occurred_at"), name="shop_click_product_time_idx"),
            models.Index(fields=("source", "occurred_at"), name="shop_click_source_time_idx"),
        ]
        ordering = ("-occurred_at", "-id")

    def __str__(self) -> str:
        return f"{self.product}: {self.source} at {self.occurred_at:%Y-%m-%d %H:%M:%S}"
