from django.contrib import admin

from .models import ClickEvent


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "source",
        "campaign",
        "occurred_at",
    )
    list_filter = ("source", "occurred_at")
    search_fields = (
        "course__title",
        "course__external_id",
        "source",
        "campaign",
    )
    readonly_fields = (
        "course",
        "source",
        "campaign",
        "occurred_at",
    )
    list_select_related = ("course", "course__provider")
    date_hierarchy = "occurred_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
