from django.db import models
from django.utils import timezone

from courses.models import Course
from providers.models import Provider


class DiscoveryRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    provider = models.ForeignKey(
        Provider,
        on_delete=models.PROTECT,
        related_name="discovery_runs",
    )
    source = models.CharField(max_length=500, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    records_found = models.PositiveIntegerField(default=0)
    records_new = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "discovery_runs"
        indexes = [
            models.Index(
                fields=("provider", "started_at"),
                name="discovery_runs_provider_idx",
            ),
            models.Index(
                fields=("status", "started_at"),
                name="discovery_runs_status_idx",
            ),
        ]
        ordering = ("-started_at", "id")

    def __str__(self) -> str:
        return f"{self.provider} discovery run #{self.pk or 'new'}"


class DiscoveryObservation(models.Model):
    run = models.ForeignKey(
        DiscoveryRun,
        on_delete=models.CASCADE,
        related_name="observations",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        related_name="discovery_observations",
        null=True,
        blank=True,
    )
    external_id = models.CharField(max_length=100)
    source_url = models.TextField()
    observed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "discovery_observations"
        indexes = [
            models.Index(
                fields=("run", "observed_at"),
                name="discovery_observation_run_idx",
            ),
            models.Index(
                fields=("external_id",),
                name="discovery_external_id_idx",
            ),
        ]
        ordering = ("observed_at", "id")

    def __str__(self) -> str:
        return f"{self.external_id} in run #{self.run_id}"
