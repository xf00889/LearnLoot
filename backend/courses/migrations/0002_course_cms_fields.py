from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="editorial_description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="course",
            name="editorial_image",
            field=models.FileField(
                blank=True,
                upload_to="courses/editorial/%Y/%m/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=("jpg", "jpeg", "png", "webp", "avif")
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="editorial_title",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="course",
            name="meta_description",
            field=models.CharField(blank=True, max_length=320),
        ),
        migrations.AddField(
            model_name="course",
            name="meta_keywords",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="course",
            name="seo_title",
            field=models.CharField(blank=True, max_length=70),
        ),
        migrations.AddField(
            model_name="course",
            name="social_image",
            field=models.FileField(
                blank=True,
                upload_to="courses/social/%Y/%m/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=("jpg", "jpeg", "png", "webp", "avif")
                    )
                ],
            ),
        ),
    ]
