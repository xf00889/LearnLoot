from django.contrib import admin, messages
from django.utils import timezone

from .models import ShoppingClickEvent, ShoppingPost, ShoppingProduct


class ShoppingProductInline(admin.StackedInline):
    model = ShoppingProduct
    extra = 0
    fields = (
        "position",
        "name",
        "slug",
        "image",
        "short_description",
        "affiliate_url",
        ("displayed_price", "original_price", "currency"),
        "badge",
        "pros",
        "cons",
        ("is_active", "expires_at"),
    )
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("position", "id")
    show_change_link = True


@admin.register(ShoppingPost)
class ShoppingPostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "post_type",
        "status",
        "is_featured",
        "active_product_count",
        "published_at",
        "updated_at",
    )
    list_filter = ("status", "post_type", "is_featured")
    search_fields = (
        "title",
        "slug",
        "excerpt",
        "body",
        "seo_title",
        "meta_description",
        "meta_keywords",
        "products__name",
    )
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (
            "Editorial content",
            {
                "fields": (
                    ("post_type", "status", "is_featured"),
                    "title",
                    "slug",
                    "excerpt",
                    "body",
                    "cover_image",
                    "published_at",
                ),
            },
        ),
        (
            "SEO metadata",
            {
                "description": (
                    "Use a unique title and description that accurately summarize this page. "
                    "Meta keywords are stored for compatibility but are not the primary SEO signal."
                ),
                "fields": ("seo_title", "meta_description", "meta_keywords"),
            },
        ),
        (
            "Audit",
            {"classes": ("collapse",), "fields": ("created_at", "updated_at")},
        ),
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = (ShoppingProductInline,)
    actions = ("publish_selected", "move_to_draft", "archive_selected")
    date_hierarchy = "published_at"

    @admin.display(description="Active items")
    def active_product_count(self, post):
        return post.products.filter(is_active=True).count()

    @admin.action(description="Publish selected posts", permissions=["change"])
    def publish_selected(self, request, queryset):
        now = timezone.now()
        updated = 0
        for post in queryset:
            post.status = ShoppingPost.Status.PUBLISHED
            if post.published_at is None:
                post.published_at = now
            post.save(update_fields=("status", "published_at", "updated_at"))
            updated += 1
        self.message_user(request, f"Published {updated} post(s).", messages.SUCCESS)

    @admin.action(description="Move selected posts to draft", permissions=["change"])
    def move_to_draft(self, request, queryset):
        updated = queryset.update(status=ShoppingPost.Status.DRAFT)
        self.message_user(request, f"Moved {updated} post(s) to draft.", messages.SUCCESS)

    @admin.action(description="Archive selected posts", permissions=["change"])
    def archive_selected(self, request, queryset):
        updated = queryset.update(status=ShoppingPost.Status.ARCHIVED)
        self.message_user(request, f"Archived {updated} post(s).", messages.SUCCESS)


@admin.register(ShoppingProduct)
class ShoppingProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "post",
        "position",
        "is_active",
        "displayed_price",
        "currency",
        "expires_at",
        "updated_at",
    )
    list_filter = ("is_active", "post__post_type", "currency")
    search_fields = ("name", "slug", "short_description", "post__title", "affiliate_url")
    list_select_related = ("post",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("post", "position")


@admin.register(ShoppingClickEvent)
class ShoppingClickEventAdmin(admin.ModelAdmin):
    list_display = ("product", "post_title", "source", "campaign", "occurred_at")
    list_filter = ("source",)
    search_fields = ("product__name", "product__post__title", "campaign")
    list_select_related = ("product", "product__post")
    readonly_fields = ("product", "source", "campaign", "occurred_at")
    date_hierarchy = "occurred_at"

    @admin.display(description="Post")
    def post_title(self, event):
        return event.product.post.title

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
