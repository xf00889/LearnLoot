from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0002_contentcategory"),
        ("shopping", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="shoppingpost",
            name="language",
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AddField(
            model_name="shoppingpost",
            name="category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="shopping_posts", to="cms.contentcategory"),
        ),
        migrations.AddField(
            model_name="shoppingproduct",
            name="content",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="shoppingproduct",
            name="language",
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AddField(
            model_name="shoppingproduct",
            name="category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="shopping_products", to="cms.contentcategory"),
        ),
    ]
