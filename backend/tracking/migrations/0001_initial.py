# Generated for LearnLoot Phase 9.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import tracking.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AffiliateLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("url", models.TextField(validators=[tracking.validators.validate_https_destination])),
                ("network", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive")], default="inactive", max_length=20)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="affiliate_links", to="courses.course")),
            ],
            options={
                "db_table": "affiliate_links",
                "ordering": ("course__title", "id"),
            },
        ),
        migrations.CreateModel(
            name="ClickEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("destination_kind", models.CharField(choices=[("provider", "Provider"), ("affiliate", "Affiliate")], max_length=20)),
                ("source", models.CharField(default="course_page", max_length=50)),
                ("campaign", models.CharField(blank=True, max_length=100)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("affiliate_link", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="click_events", to="tracking.affiliatelink")),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="click_events", to="courses.course")),
            ],
            options={
                "db_table": "click_events",
                "ordering": ("-occurred_at", "-id"),
            },
        ),
        migrations.AddConstraint(
            model_name="affiliatelink",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "active")), fields=("course",), name="affiliate_one_active_course"),
        ),
        migrations.AddIndex(
            model_name="affiliatelink",
            index=models.Index(fields=["status", "updated_at"], name="affiliate_status_updated_idx"),
        ),
        migrations.AddIndex(
            model_name="clickevent",
            index=models.Index(fields=["course", "occurred_at"], name="click_course_time_idx"),
        ),
        migrations.AddIndex(
            model_name="clickevent",
            index=models.Index(fields=["source", "occurred_at"], name="click_source_time_idx"),
        ),
    ]
