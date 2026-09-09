from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import shopping.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ShoppingPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("post_type", models.CharField(choices=[("top_10", "Top 10 / ranked list"), ("flash_deals", "Flash deals"), ("buying_guide", "Buying guide"), ("roundup", "Product roundup"), ("article", "Article")], default="top_10", max_length=30)),
                ("title", models.CharField(max_length=300)),
                ("slug", models.SlugField(max_length=320, unique=True)),
                ("excerpt", models.CharField(blank=True, max_length=500)),
                ("body", models.TextField(blank=True)),
                ("cover_image", models.FileField(blank=True, upload_to="shopping/posts/%Y/%m/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=("jpg", "jpeg", "png", "webp", "avif"))])),
                ("seo_title", models.CharField(blank=True, max_length=70)),
                ("meta_description", models.CharField(blank=True, max_length=320)),
                ("meta_keywords", models.CharField(blank=True, max_length=500)),
                ("is_featured", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")], default="draft", max_length=20)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "shopping_posts", "ordering": ("-published_at", "-updated_at", "id")},
        ),
        migrations.CreateModel(
            name="ShoppingProduct",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveSmallIntegerField()),
                ("name", models.CharField(max_length=300)),
                ("slug", models.SlugField(max_length=220)),
                ("image", models.FileField(blank=True, upload_to="shopping/products/%Y/%m/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=("jpg", "jpeg", "png", "webp", "avif"))])),
                ("short_description", models.TextField(blank=True)),
                ("affiliate_url", models.URLField(max_length=2000, validators=[shopping.validators.validate_https_affiliate_url])),
                ("displayed_price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("original_price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("currency", models.CharField(default="PHP", max_length=3)),
                ("badge", models.CharField(blank=True, max_length=100)),
                ("pros", models.TextField(blank=True)),
                ("cons", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="products", to="shopping.shoppingpost")),
            ],
            options={"db_table": "shopping_products", "ordering": ("position", "id")},
        ),
        migrations.CreateModel(
            name="ShoppingClickEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(default="shopping_page", max_length=50)),
                ("campaign", models.CharField(blank=True, max_length=100)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="click_events", to="shopping.shoppingproduct")),
            ],
            options={"db_table": "shopping_click_events", "ordering": ("-occurred_at", "-id")},
        ),
        migrations.AddIndex(model_name="shoppingpost", index=models.Index(fields=["status", "-published_at"], name="shop_post_status_pub_idx")),
        migrations.AddIndex(model_name="shoppingpost", index=models.Index(fields=["post_type", "status"], name="shop_post_type_status_idx")),
        migrations.AddConstraint(model_name="shoppingproduct", constraint=models.UniqueConstraint(fields=("post", "position"), name="shop_product_post_position_uniq")),
        migrations.AddConstraint(model_name="shoppingproduct", constraint=models.UniqueConstraint(fields=("post", "slug"), name="shop_product_post_slug_uniq")),
        migrations.AddIndex(model_name="shoppingproduct", index=models.Index(fields=["post", "is_active", "position"], name="shop_product_active_pos_idx")),
        migrations.AddIndex(model_name="shoppingproduct", index=models.Index(fields=["expires_at"], name="shop_product_expiry_idx")),
        migrations.AddIndex(model_name="shoppingclickevent", index=models.Index(fields=["product", "occurred_at"], name="shop_click_product_time_idx")),
        migrations.AddIndex(model_name="shoppingclickevent", index=models.Index(fields=["source", "occurred_at"], name="shop_click_source_time_idx")),
    ]
