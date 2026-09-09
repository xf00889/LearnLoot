from django.contrib import admin

from .models import MediaAsset


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("title", "file", "content_type", "size_bytes", "uploaded_by", "created_at")
    search_fields = ("title", "alt_text", "file")
    readonly_fields = ("content_type", "size_bytes", "uploaded_by", "created_at")
