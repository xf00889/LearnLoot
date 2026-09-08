# Generated for LearnLoot Phase 2 core domain.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CoursePrice",
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
                    "amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                    ),
                ),
                ("currency", models.CharField(max_length=3)),
                ("is_free", models.BooleanField(default=False)),
                ("price_type", models.CharField(blank=True, max_length=30)),
                ("observed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("source_url", models.TextField(blank=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prices",
                        to="courses.course",
                    ),
                ),
            ],
            options={
                "db_table": "course_prices",
                "ordering": ("-observed_at", "id"),
                "indexes": [
                    models.Index(
                        fields=["course", "observed_at"],
                        name="course_prices_observed_idx",
                    ),
                    models.Index(
                        fields=["course", "is_free", "observed_at"],
                        name="course_prices_free_idx",
                    ),
                ],
            },
        ),
    ]