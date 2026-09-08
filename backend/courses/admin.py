from django.contrib import admin, messages

from discovery.models import DiscoveryObservation
from pricing.models import CoursePrice

from .models import Course, CourseSource


class ReadOnlyInlineMixin:
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class CoursePriceInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = CoursePrice
    fields = (
        "amount",
        "currency",
        "is_free",
        "price_type",
        "observed_at",
        "source_url",
    )
    readonly_fields = fields
    ordering = ("-observed_at", "-pk")


class CourseSourceInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = CourseSource
    fields = ("source_type", "source_url", "first_seen_at", "last_seen_at")
    readonly_fields = fields
    ordering = ("-last_seen_at", "-pk")


class DiscoveryObservationInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = DiscoveryObservation
    fk_name = "course"
    fields = ("run", "external_id", "source_url", "observed_at")
    readonly_fields = fields
    ordering = ("-observed_at", "-pk")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "provider",
        "external_id",
        "status",
        "rating",
        "review_count",
        "last_checked_at",
        "last_seen_at",
    )
    list_filter = ("status", "provider")
    search_fields = (
        "title",
        "external_id",
        "instructor_name",
        "slug",
        "canonical_url",
    )
    list_select_related = ("provider",)
    readonly_fields = (
        "provider",
        "external_id",
        "slug",
        "first_seen_at",
        "last_seen_at",
        "last_checked_at",
        "created_at",
        "updated_at",
    )
    inlines = (CoursePriceInline, CourseSourceInline, DiscoveryObservationInline)
    actions = ("activate_selected", "hide_selected", "archive_selected")
    date_hierarchy = "last_seen_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Activate selected courses", permissions=["change"])
    def activate_selected(self, request, queryset):
        updated = queryset.update(status=Course.Status.ACTIVE)
        self.message_user(request, f"Activated {updated} course(s).", messages.SUCCESS)

    @admin.action(description="Hide selected courses", permissions=["change"])
    def hide_selected(self, request, queryset):
        updated = queryset.update(status=Course.Status.HIDDEN)
        self.message_user(request, f"Hidden {updated} course(s).", messages.SUCCESS)

    @admin.action(description="Archive selected courses", permissions=["change"])
    def archive_selected(self, request, queryset):
        updated = queryset.update(status=Course.Status.ARCHIVED)
        self.message_user(request, f"Archived {updated} course(s).", messages.SUCCESS)


@admin.register(CourseSource)
class CourseSourceAdmin(admin.ModelAdmin):
    list_display = ("course", "source_type", "first_seen_at", "last_seen_at")
    list_filter = ("source_type",)
    search_fields = ("course__title", "course__external_id", "source_url")
    readonly_fields = (
        "course",
        "source_url",
        "source_type",
        "first_seen_at",
        "last_seen_at",
    )
    list_select_related = ("course",)
    date_hierarchy = "last_seen_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False