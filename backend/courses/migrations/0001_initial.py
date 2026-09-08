# Generated for LearnLoot Phase 2 core domain.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("providers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
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
                ("title", models.CharField(max_length=500)),
                ("slug", models.SlugField(db_index=False, max_length=600)),
                ("canonical_url", models.TextField()),
                ("thumbnail_url", models.TextField(blank=True)),
                ("instructor_name", models.CharField(blank=True, max_length=255)),
                (
                    "rating",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=3,
                        null=True,
                    ),
                ),
                ("review_count", models.PositiveIntegerField(blank=True, null=True)),
                ("student_count", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "duration_minutes",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("hidden", "Hidden"),
                            ("archived", "Archived"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("first_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_checked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="courses",
                        to="providers.provider",
                    ),
                ),
            ],
            options={
                "db_table": "courses",
                "ordering": ("-last_seen_at", "id"),
                "indexes": [
                    models.Index(
                        fields=["provider", "status"],
                        name="courses_provider_status_idx",
                    ),
                    models.Index(
                        fields=["last_checked_at"],
                        name="courses_last_checked_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("provider", "external_id"),
                        name="course_provider_external_uniq",
                    ),
                    models.UniqueConstraint(
                        fields=("provider", "slug"),
                        name="course_provider_slug_uniq",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="CourseSource",
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
                ("source_url", models.TextField()),
                ("source_type", models.CharField(max_length=50)),
                ("first_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sources",
                        to="courses.course",
                    ),
                ),
            ],
            options={
                "db_table": "course_sources",
                "ordering": ("-last_seen_at", "id"),
                "indexes": [
                    models.Index(
                        fields=["course", "last_seen_at"],
                        name="course_sources_seen_idx",
                    ),
                ],
            },
        ),
    ]