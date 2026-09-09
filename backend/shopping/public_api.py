from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db.models import Q, QuerySet
from django.http import Http404, HttpRequest, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import ShoppingPost, ShoppingProduct
from .services import ShoppingDestinationError, resolve_shopping_destination

DEFAULT_LIMIT = 24
MAX_LIMIT = 100
SITEMAP_MAX_POSTS = 5000

AFFILIATE_DISCLOSURE = (
    "This page contains affiliate links. LearnLoot may earn a commission from "
    "qualifying purchases at no additional cost to you."
)


def _limit_from_request(request: HttpRequest) -> int:
    raw = request.GET.get("limit", str(DEFAULT_LIMIT))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(1, min(value, MAX_LIMIT))


def _base_post_queryset() -> QuerySet[ShoppingPost]:
    return (
        ShoppingPost.objects.filter(
            status=ShoppingPost.Status.PUBLISHED,
            published_at__isnull=False,
            published_at__lte=timezone.now(),
        )
        .select_related("category")
        .prefetch_related("products__category")
        .order_by("-is_featured", "-published_at", "-updated_at", "id")
    )


def _public_post_url(post: ShoppingPost) -> str:
    base_url = str(getattr(settings, "LEARNLOOT_PUBLIC_BASE_URL", "")).rstrip("/")
    path = f"/shop/{post.slug}"
    return f"{base_url}{path}" if base_url else path


def _file_url(request: HttpRequest, field) -> str:
    if not field:
        return ""
    try:
        return request.build_absolute_uri(field.url)
    except (ValueError, AttributeError):
        return ""


def _active_products(post: ShoppingPost) -> list[ShoppingProduct]:
    now = timezone.now()
    products = []
    for product in post.products.all():
        if not product.is_active:
            continue
        if product.expires_at is not None and product.expires_at <= now:
            continue
        try:
            resolve_shopping_destination(product)
        except ShoppingDestinationError:
            continue
        products.append(product)
    return sorted(products, key=lambda item: (item.position, item.id))


def _outbound_url(request: HttpRequest, post: ShoppingPost, product: ShoppingProduct) -> str:
    path = reverse(
        "shopping-outbound:shopping-outbound-redirect",
        kwargs={"post_slug": post.slug, "product_slug": product.slug},
    )
    return request.build_absolute_uri(path)


def _product_payload(request: HttpRequest, post: ShoppingPost, product: ShoppingProduct) -> dict[str, Any]:
    return {
        "id": product.id,
        "position": product.position,
        "name": product.name,
        "title": product.name,
        "slug": product.slug,
        "image_url": _file_url(request, product.image),
        "short_description": product.short_description,
        "content": product.content,
        "category": ({"name": product.category.name, "slug": product.category.slug} if product.category else None),
        "language": product.language,
        "displayed_price": str(product.displayed_price) if product.displayed_price is not None else None,
        "original_price": str(product.original_price) if product.original_price is not None else None,
        "currency": product.currency,
        "badge": product.badge,
        "pros": product.pros,
        "cons": product.cons,
        "expires_at": product.expires_at.isoformat() if product.expires_at else None,
        "outbound_url": _outbound_url(request, post, product),
    }


def _post_summary(request: HttpRequest, post: ShoppingPost) -> dict[str, Any]:
    return {
        "id": post.id,
        "post_type": post.post_type,
        "post_type_label": post.get_post_type_display(),
        "title": post.title,
        "slug": post.slug,
        "url": _public_post_url(post),
        "excerpt": post.excerpt,
        "short_description": post.excerpt,
        "category": ({"name": post.category.name, "slug": post.category.slug} if post.category else None),
        "language": post.language,
        "cover_image_url": _file_url(request, post.cover_image),
        "is_featured": post.is_featured,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "updated_at": post.updated_at.isoformat(),
    }


def _post_detail(request: HttpRequest, post: ShoppingPost) -> dict[str, Any]:
    payload = _post_summary(request, post)
    payload.update(
        {
            "body": post.body,
            "affiliate_disclosure": AFFILIATE_DISCLOSURE,
            "seo": {
                "title": post.public_seo_title,
                "description": post.public_meta_description,
                "keywords": post.meta_keywords,
                "social_image_url": _file_url(request, post.cover_image),
            },
            "products": [_product_payload(request, post, product) for product in _active_products(post)],
        }
    )
    return payload


def _filtered_posts(request: HttpRequest) -> QuerySet[ShoppingPost]:
    queryset = _base_post_queryset()
    post_type = request.GET.get("type", "").strip()
    valid_types = {value for value, _ in ShoppingPost.PostType.choices}
    if post_type in valid_types:
        queryset = queryset.filter(post_type=post_type)

    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(excerpt__icontains=query)
            | Q(body__icontains=query)
            | Q(meta_keywords__icontains=query)
            | Q(category__name__icontains=query)
            | Q(language__icontains=query)
            | Q(products__name__icontains=query)
        ).distinct()
    return queryset


def get_public_post_or_404(post_slug: str) -> ShoppingPost:
    try:
        return _base_post_queryset().get(slug=post_slug)
    except ShoppingPost.DoesNotExist as exc:
        raise Http404("Shopping post is not public") from exc


@require_GET
def public_post_list(request: HttpRequest) -> JsonResponse:
    posts = list(_filtered_posts(request)[: _limit_from_request(request)])
    return JsonResponse(
        {
            "generated_at": timezone.now().isoformat(),
            "count": len(posts),
            "results": [_post_summary(request, post) for post in posts],
        }
    )


@require_GET
def public_post_sitemap(request: HttpRequest) -> JsonResponse:
    entries = [
        {"url": _public_post_url(post), "last_modified": post.updated_at.isoformat()}
        for post in _base_post_queryset()[:SITEMAP_MAX_POSTS]
    ]
    return JsonResponse({"results": entries})


@require_GET
def public_post_detail(request: HttpRequest, post_slug: str) -> JsonResponse:
    return JsonResponse(_post_detail(request, get_public_post_or_404(post_slug)))
