# Generated for LearnLoot Phase 6.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("courses", "0001_initial"),
        ("pricing", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminOverride",
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
                (
                    "decision",
                    models.CharField(
                        choices=[
                            ("auto", "Automatic rules"),
                            ("force_eligible", "Force eligible"),
                            ("force_ineligible", "Force ineligible"),
                        ],
                        default="auto",
                        max_length=30,
                    ),
                ),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="publication_override",
                        to="courses.course",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="learnloot_publication_overrides",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "admin_overrides",
                "ordering": ("course__title", "id"),
            },
        ),
        migrations.CreateModel(
            name="DealEligibility",
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
                ("score", models.PositiveSmallIntegerField(default=0)),
                ("eligible", models.BooleanField(default=False)),
                ("override_applied", models.BooleanField(default=False)),
                ("reasons", models.JSONField(default=list)),
                ("evaluated_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "course",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="publication_eligibility",
                        to="courses.course",
                    ),
                ),
                (
                    "latest_price",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="eligibility_snapshots",
                        to="pricing.courseprice",
                    ),
                ),
            ],
            options={
                "db_table": "deal_eligibility",
                "ordering": ("-evaluated_at", "id"),
            },
        ),
        migrations.CreateModel(
            name="PublicationQueueItem",
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
                ("score", models.PositiveSmallIntegerField(default=0)),
                ("override_applied", models.BooleanField(default=False)),
                ("reasons", models.JSONField(default=list)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("queued_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="publication_queue_items",
                        to="courses.course",
                    ),
                ),
                (
                    "latest_price",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="publication_queue_items",
                        to="pricing.courseprice",
                    ),
                ),
            ],
            options={
                "db_table": "publication_queue",
                "ordering": ("-queued_at", "id"),
            },
        ),
        migrations.AddIndex(
            model_name="dealeligibility",
            index=models.Index(
                fields=["eligible", "score"],
                name="deal_eligibility_score_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="dealeligibility",
            index=models.Index(
                fields=["evaluated_at"],
                name="deal_eligibility_eval_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="publicationqueueitem",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="queued"),
                fields=("course",),
                name="publication_one_queued_course",
            ),
        ),
        migrations.AddIndex(
            model_name="publicationqueueitem",
            index=models.Index(
                fields=["status", "queued_at"],
                name="publication_status_time_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="publicationqueueitem",
            index=models.Index(
                fields=["course", "status"],
                name="publication_course_status_idx",
            ),
        ),
    ]