from django.contrib import admin

from .models import ContentCategory, MediaAsset


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("title", "file", "content_type", "size_bytes", "uploaded_by", "created_at")
    search_fields = ("title", "alt_text", "file")
    readonly_fields = ("content_type", "size_bytes", "uploaded_by", "created_at")


@admin.register(ContentCategory)
class ContentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "scope", "slug", "is_active", "updated_at")
    list_filter = ("scope", "is_active")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
