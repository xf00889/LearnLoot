from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0002_contentcategory"),
        ("courses", "0002_course_cms_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="short_description",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="course",
            name="language",
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AddField(
            model_name="course",
            name="category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="courses", to="cms.contentcategory"),
        ),
    ]
