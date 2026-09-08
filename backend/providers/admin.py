from django.contrib import admin, messages
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from django.utils.html import format_html

from discovery.models import DiscoveryRun
from discovery.registry import (
    UnsupportedDiscoveryProvider,
    get_discovery_provider_config,
    get_discovery_readiness,
    safe_source_for_display,
)
from discovery.tasks import run_provider_discovery
from publishing.models import PublicationQueueItem
from publishing.tasks import evaluate_provider_publication_candidates

from .models import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "status",
        "discovery_status",
        "last_discovery_status",
        "last_discovery_at",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("name", "slug")
    ordering = ("name",)
    readonly_fields = (
        "discovery_configuration",
        "last_successful_discovery",
        "last_failed_discovery",
        "created_at",
        "updated_at",
    )
    actions = (
        "queue_discovery",
        "queue_publication_evaluation",
        "activate_selected_providers",
        "deactivate_selected_providers",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        last_run = DiscoveryRun.objects.filter(provider=OuterRef("pk")).order_by(
            "-started_at", "-pk"
        )
        return queryset.annotate(
            _last_discovery_status=Subquery(last_run.values("status")[:1]),
            _last_discovery_at=Subquery(last_run.values("started_at")[:1]),
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status != Provider.Status.ACTIVE:
            PublicationQueueItem.objects.filter(
                course__provider=obj,
                status=PublicationQueueItem.Status.QUEUED,
            ).update(
                status=PublicationQueueItem.Status.CANCELLED,
                error_message="Provider inactive",
                updated_at=timezone.now(),
            )

    @admin.display(description="Discovery")
    def discovery_status(self, provider):
        _ready, message = get_discovery_readiness(provider)
        return message

    @admin.display(description="Last run", ordering="_last_discovery_status")
    def last_discovery_status(self, provider):
        return getattr(provider, "_last_discovery_status", None) or "Never"

    @admin.display(description="Last discovery", ordering="_last_discovery_at")
    def last_discovery_at(self, provider):
        return getattr(provider, "_last_discovery_at", None)

    @admin.display(description="Discovery configuration")
    def discovery_configuration(self, provider):
        try:
            config = get_discovery_provider_config(provider.slug)
        except UnsupportedDiscoveryProvider:
            return "No registered discovery connector"

        return format_html(
            "Source: {}<br>Access acknowledged: {}<br>Max pages: {}<br>"
            "Item limit: {}<br>Render wait: {} ms",
            safe_source_for_display(config.source),
            "yes" if config.access_approved else "no",
            config.max_pages,
            config.item_limit,
            config.render_wait_ms,
        )

    @admin.display(description="Last successful discovery")
    def last_successful_discovery(self, provider):
        if provider is None or provider.pk is None:
            return "Never"
        return (
            provider.discovery_runs.filter(status=DiscoveryRun.Status.SUCCEEDED)
            .order_by("-started_at", "-pk")
            .first()
            or "Never"
        )

    @admin.display(description="Last failed discovery")
    def last_failed_discovery(self, provider):
        if provider is None or provider.pk is None:
            return "Never"
        return (
            provider.discovery_runs.filter(status=DiscoveryRun.Status.FAILED)
            .order_by("-started_at", "-pk")
            .first()
            or "Never"
        )

    @admin.action(description="Queue discovery for selected providers", permissions=["change"])
    def queue_discovery(self, request, queryset):
        queued = 0
        skipped: list[str] = []

        for provider in queryset.order_by("pk"):
            ready, reason = get_discovery_readiness(provider)
            if not ready:
                skipped.append(f"{provider.name}: {reason}")
                continue

            run_provider_discovery.delay(provider.pk)
            queued += 1

        if queued:
            self.message_user(
                request,
                f"Queued discovery for {queued} provider(s).",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                "Skipped: " + "; ".join(skipped),
                level=messages.WARNING,
            )


    @admin.action(
        description="Queue publication evaluation for selected providers",
        permissions=["change"],
    )
    def queue_publication_evaluation(self, request, queryset):
        queued = 0
        for provider in queryset.order_by("pk"):
            evaluate_provider_publication_candidates.delay(provider.pk)
            queued += 1

        self.message_user(
            request,
            f"Queued publication evaluation for {queued} provider(s).",
            level=messages.SUCCESS,
        )

    @admin.action(description="Activate selected providers", permissions=["change"])
    def activate_selected_providers(self, request, queryset):
        updated = queryset.update(status=Provider.Status.ACTIVE)
        self.message_user(
            request,
            f"Activated {updated} provider(s).",
            level=messages.SUCCESS,
        )

    @admin.action(description="Deactivate selected providers", permissions=["change"])
    def deactivate_selected_providers(self, request, queryset):
        provider_ids = list(queryset.values_list("pk", flat=True))
        updated = queryset.update(status=Provider.Status.INACTIVE)
        PublicationQueueItem.objects.filter(
            course__provider_id__in=provider_ids,
            status=PublicationQueueItem.Status.QUEUED,
        ).update(
            status=PublicationQueueItem.Status.CANCELLED,
            error_message="Provider inactive",
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f"Deactivated {updated} provider(s).",
            level=messages.SUCCESS,
        )