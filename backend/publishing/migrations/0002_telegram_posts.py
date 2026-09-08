# Generated for LearnLoot Phase 7.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("publishing", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramPost",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sending", "Sending"),
                            ("retry_wait", "Waiting to retry"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                            ("ambiguous", "Ambiguous outcome"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("telegram_message_id", models.BigIntegerField(blank=True, null=True)),
                ("message_text", models.TextField()),
                ("landing_url", models.TextField()),
                ("payload_sha256", models.CharField(max_length=64)),
                ("target_fingerprint", models.CharField(max_length=64)),
                ("task_id", models.CharField(blank=True, max_length=255)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("first_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "queue_item",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="telegram_post",
                        to="publishing.publicationqueueitem",
                    ),
                ),
            ],
            options={
                "db_table": "telegram_posts",
                "ordering": ("-created_at", "id"),
            },
        ),
        migrations.AddIndex(
            model_name="telegrampost",
            index=models.Index(
                fields=["status", "last_attempt_at"],
                name="telegram_status_attempt_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="telegrampost",
            index=models.Index(
                fields=["sent_at"],
                name="telegram_sent_at_idx",
            ),
        ),
    ]