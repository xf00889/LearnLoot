from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope", models.CharField(choices=[("course", "Courses"), ("affiliate", "Affiliate")], max_length=20)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=140)),
                ("description", models.CharField(blank=True, max_length=300)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "cms_categories", "ordering": ("scope", "name", "id")},
        ),
        migrations.AddConstraint(
            model_name="contentcategory",
            constraint=models.UniqueConstraint(fields=("scope", "slug"), name="cms_category_scope_slug_uniq"),
        ),
        migrations.AddIndex(
            model_name="contentcategory",
            index=models.Index(fields=["scope", "is_active", "name"], name="cms_category_scope_active_idx"),
        ),
    ]
