from django.contrib import admin

from .models import CoursePrice


@admin.register(CoursePrice)
class CoursePriceAdmin(admin.ModelAdmin):
    list_display = ("course", "amount", "currency", "is_free", "price_type", "observed_at")
    list_filter = ("is_free", "currency", "price_type")
    search_fields = ("course__title", "course__external_id")
    raw_id_fields = ("course",)
    date_hierarchy = "observed_at"