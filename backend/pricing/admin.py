from django.contrib import admin

from .models import CoursePrice


@admin.register(CoursePrice)
class CoursePriceAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "amount",
        "currency",
        "is_free",
        "price_type",
        "observed_at",
    )
    list_filter = ("is_free", "currency", "price_type")
    search_fields = ("course__title", "course__external_id", "source_url")
    readonly_fields = (
        "course",
        "amount",
        "currency",
        "is_free",
        "price_type",
        "observed_at",
        "source_url",
    )
    list_select_related = ("course",)
    date_hierarchy = "observed_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False