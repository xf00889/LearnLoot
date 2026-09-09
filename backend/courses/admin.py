from django.contrib import admin, messages
from django.utils import timezone

from discovery.models import DiscoveryObservation
from pricing.models import CoursePrice
from publishing.models import DealEligibility, PublicationQueueItem
from publishing.tasks import evaluate_course_publication_candidate

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


class DealEligibilityInline(ReadOnlyInlineMixin, admin.StackedInline):
    model = DealEligibility
    fields = (
        "eligible",
        "score",
        "override_applied",
        "reasons",
        "latest_price",
        "evaluated_at",
    )
    readonly_fields = fields
    max_num = 1


class PublicationQueueInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = PublicationQueueItem
    fields = (
        "status",
        "score",
        "override_applied",
        "queued_at",
        "sent_at",
        "attempts",
    )
    readonly_fields = fields
    ordering = ("-queued_at", "-pk")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "public_title_display",
        "provider",
        "external_id",
        "status",
        "cms_customized",
        "rating",
        "review_count",
        "publication_eligible",
        "publication_score",
        "last_checked_at",
    )
    list_filter = ("status", "provider")
    search_fields = (
        "title",
        "editorial_title",
        "external_id",
        "instructor_name",
        "slug",
        "canonical_url",
        "description",
        "editorial_description",
        "seo_title",
        "meta_description",
        "meta_keywords",
    )
    list_select_related = ("provider",)
    readonly_fields = (
        "provider",
        "external_id",
        "title",
        "canonical_url",
        "thumbnail_url",
        "instructor_name",
        "rating",
        "review_count",
        "student_count",
        "duration_minutes",
        "description",
        "first_seen_at",
        "last_seen_at",
        "last_checked_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "CMS public content",
            {
                "description": (
                    "These operator-controlled fields are never overwritten by a "
                    "future discovery run. Leave an override blank to use the latest "
                    "scraped Udemy metadata."
                ),
                "fields": (
                    "status",
                    "slug",
                    "editorial_title",
                    "editorial_description",
                    "editorial_image",
                ),
            },
        ),
        (
            "SEO and social metadata",
            {
                "description": (
                    "Unique metadata for the public course landing page. Meta keywords "
                    "are supported for compatibility even though major search engines "
                    "may ignore them."
                ),
                "fields": (
                    "seo_title",
                    "meta_description",
                    "meta_keywords",
                    "social_image",
                ),
            },
        ),
        (
            "Scraped provider data",
            {
                "classes": ("collapse",),
                "description": (
                    "Source-controlled metadata refreshed by discovery. Edit the CMS "
                    "override fields above instead of changing these values."
                ),
                "fields": (
                    "provider",
                    "external_id",
                    "title",
                    "canonical_url",
                    "thumbnail_url",
                    "instructor_name",
                    "rating",
                    "review_count",
                    "student_count",
                    "duration_minutes",
                    "description",
                ),
            },
        ),
        (
            "Discovery timestamps",
            {
                "classes": ("collapse",),
                "fields": (
                    "first_seen_at",
                    "last_seen_at",
                    "last_checked_at",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )
    inlines = (
        CoursePriceInline,
        CourseSourceInline,
        DiscoveryObservationInline,
        DealEligibilityInline,
        PublicationQueueInline,
    )
    actions = (
        "queue_publication_evaluation",
        "activate_selected",
        "hide_selected",
        "archive_selected",
    )
    date_hierarchy = "last_seen_at"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("publication_eligibility")

    @admin.display(description="Course", ordering="title")
    def public_title_display(self, course):
        return course.public_title

    @admin.display(description="CMS edited", boolean=True)
    def cms_customized(self, course):
        return course.is_editorially_customized

    @admin.display(description="Publish eligible", boolean=True)
    def publication_eligible(self, course):
        try:
            return course.publication_eligibility.eligible
        except DealEligibility.DoesNotExist:
            return None

    @admin.display(description="Deal score")
    def publication_score(self, course):
        try:
            return course.publication_eligibility.score
        except DealEligibility.DoesNotExist:
            return None

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status != Course.Status.ACTIVE:
            PublicationQueueItem.objects.filter(
                course=obj,
                status=PublicationQueueItem.Status.QUEUED,
            ).update(
                status=PublicationQueueItem.Status.CANCELLED,
                error_message="Course is not active",
                updated_at=timezone.now(),
            )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(
        description="Queue publication evaluation for selected courses",
        permissions=["change"],
    )
    def queue_publication_evaluation(self, request, queryset):
        queued = 0
        for course_id in queryset.order_by("pk").values_list("pk", flat=True):
            evaluate_course_publication_candidate.delay(course_id)
            queued += 1

        self.message_user(
            request,
            f"Queued publication evaluation for {queued} course(s).",
            messages.SUCCESS,
        )

    @admin.action(description="Activate selected courses", permissions=["change"])
    def activate_selected(self, request, queryset):
        updated = queryset.update(status=Course.Status.ACTIVE)
        self.message_user(request, f"Activated {updated} course(s).", messages.SUCCESS)

    @admin.action(description="Hide selected courses", permissions=["change"])
    def hide_selected(self, request, queryset):
        course_ids = list(queryset.values_list("pk", flat=True))
        updated = queryset.update(status=Course.Status.HIDDEN)
        PublicationQueueItem.objects.filter(
            course_id__in=course_ids,
            status=PublicationQueueItem.Status.QUEUED,
        ).update(
            status=PublicationQueueItem.Status.CANCELLED,
            error_message="Course hidden by admin",
            updated_at=timezone.now(),
        )
        self.message_user(request, f"Hidden {updated} course(s).", messages.SUCCESS)

    @admin.action(description="Archive selected courses", permissions=["change"])
    def archive_selected(self, request, queryset):
        course_ids = list(queryset.values_list("pk", flat=True))
        updated = queryset.update(status=Course.Status.ARCHIVED)
        PublicationQueueItem.objects.filter(
            course_id__in=course_ids,
            status=PublicationQueueItem.Status.QUEUED,
        ).update(
            status=PublicationQueueItem.Status.CANCELLED,
            error_message="Course archived by admin",
            updated_at=timezone.now(),
        )
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
