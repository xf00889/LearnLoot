from django.contrib import admin

from .models import DiscoveryObservation, DiscoveryRun


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
    search_fields = ("source", "error_message")
    raw_id_fields = ("provider",)
    date_hierarchy = "started_at"


@admin.register(DiscoveryObservation)
class DiscoveryObservationAdmin(admin.ModelAdmin):
    list_display = ("external_id", "run", "course", "observed_at")
    search_fields = ("external_id", "source_url", "course__title")
    raw_id_fields = ("run", "course")
    date_hierarchy = "observed_at"