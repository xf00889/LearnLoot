from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="MediaAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="cms/media/%Y/%m/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=("jpg", "jpeg", "png", "webp", "avif"))])),
                ("title", models.CharField(blank=True, max_length=200)),
                ("alt_text", models.CharField(blank=True, max_length=300)),
                ("content_type", models.CharField(blank=True, max_length=100)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="learnloot_media_assets", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "cms_media_assets", "ordering": ("-created_at", "-id")},
        )
    ]
