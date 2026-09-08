from django.contrib import admin

from .models import DiscoveryObservation, DiscoveryRun


class DiscoveryObservationInline(admin.TabularInline):
    model = DiscoveryObservation
    extra = 0
    can_delete = False
    fields = ("external_id", "course", "source_url", "observed_at")
    readonly_fields = fields
    ordering = ("observed_at", "pk")
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(DiscoveryRun)
class DiscoveryRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "provider",
        "status",
        "source",
        "records_found",
        "records_new",
        "records_updated",
        "records_failed",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "provider")
    search_fields = ("source", "error_message", "provider__name", "provider__slug")
    readonly_fields = (
        "provider",
        "source",
        "started_at",
        "finished_at",
        "status",
        "records_found",
        "records_new",
        "records_updated",
        "records_failed",
        "error_message",
    )
    list_select_related = ("provider",)
    date_hierarchy = "started_at"
    inlines = (DiscoveryObservationInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DiscoveryObservation)
class DiscoveryObservationAdmin(admin.ModelAdmin):
    list_display = ("external_id", "run", "course", "observed_at")
    search_fields = ("external_id", "source_url", "course__title")
    readonly_fields = ("run", "course", "external_id", "source_url", "observed_at")
    list_select_related = ("run", "course")
    date_hierarchy = "observed_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False