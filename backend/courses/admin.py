from django.contrib import admin

from .models import Course, CourseSource


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "provider",
        "external_id",
        "status",
        "rating",
        "last_checked_at",
        "last_seen_at",
    )
    list_filter = ("status", "provider")
    search_fields = ("title", "external_id", "instructor_name", "slug")
    raw_id_fields = ("provider",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CourseSource)
class CourseSourceAdmin(admin.ModelAdmin):
    list_display = ("course", "source_type", "first_seen_at", "last_seen_at")
    list_filter = ("source_type",)
    search_fields = ("course__title", "course__external_id", "source_url")
    raw_id_fields = ("course",)