from django.contrib import admin

from .models import AffiliateLink, ClickEvent


@admin.register(AffiliateLink)
class AffiliateLinkAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "network",
        "status",
        "updated_at",
    )
    list_filter = ("status", "network")
    search_fields = (
        "course__title",
        "course__external_id",
        "network",
        "url",
        "note",
    )
    autocomplete_fields = ("course",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("course", "course__provider")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "destination_kind",
        "source",
        "campaign",
        "occurred_at",
    )
    list_filter = ("destination_kind", "source", "occurred_at")
    search_fields = (
        "course__title",
        "course__external_id",
        "source",
        "campaign",
        "affiliate_link__network",
    )
    readonly_fields = (
        "course",
        "affiliate_link",
        "destination_kind",
        "source",
        "campaign",
        "occurred_at",
    )
    list_select_related = ("course", "course__provider", "affiliate_link")
    date_hierarchy = "occurred_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
