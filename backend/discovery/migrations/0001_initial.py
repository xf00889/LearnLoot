# Generated for LearnLoot Phase 2 core domain.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("courses", "0001_initial"),
        ("providers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DiscoveryRun",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("source", models.CharField(blank=True, max_length=500)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        default="running",
                        max_length=20,
                    ),
                ),
                ("records_found", models.PositiveIntegerField(default=0)),
                ("records_new", models.PositiveIntegerField(default=0)),
                ("records_updated", models.PositiveIntegerField(default=0)),
                ("records_failed", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="discovery_runs",
                        to="providers.provider",
                    ),
                ),
            ],
            options={
                "db_table": "discovery_runs",
                "ordering": ("-started_at", "id"),
                "indexes": [
                    models.Index(
                        fields=["provider", "started_at"],
                        name="discovery_runs_provider_idx",
                    ),
                    models.Index(
                        fields=["status", "started_at"],
                        name="discovery_runs_status_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="DiscoveryObservation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("external_id", models.CharField(max_length=100)),
                ("source_url", models.TextField()),
                ("observed_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "course",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="discovery_observations",
                        to="courses.course",
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="observations",
                        to="discovery.discoveryrun",
                    ),
                ),
            ],
            options={
                "db_table": "discovery_observations",
                "ordering": ("observed_at", "id"),
                "indexes": [
                    models.Index(
                        fields=["run", "observed_at"],
                        name="discovery_observation_run_idx",
                    ),
                    models.Index(
                        fields=["external_id"],
                        name="discovery_external_id_idx",
                    ),
                ],
            },
        ),
    ]