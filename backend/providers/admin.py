from django.contrib import admin

from .models import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    ordering = ("name",)