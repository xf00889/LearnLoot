from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path

from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from courses.models import Course
from discovery.models import DiscoveryRun
from pricing.models import CoursePrice
from publishing.models import PublicationQueueItem, TelegramPost
from shopping.models import ShoppingClickEvent, ShoppingPost, ShoppingProduct
from tracking.models import ClickEvent

from .models import ContentCategory, MediaAsset
from .sanitizer import sanitize_rich_html

MAX_PAGE_SIZE = 100
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif"}


def _staff_required(view):
    @wraps(view)
    def wrapped(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Authentication required."}, status=401)
        if not request.user.is_staff:
            return JsonResponse({"detail": "Staff access required."}, status=403)
        return view(request, *args, **kwargs)

    return wrapped


def _json_body(request: HttpRequest) -> dict:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid JSON request body.") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON request body must be an object.")
    return payload


def _file_url(request: HttpRequest, field) -> str:
    if not field:
        return ""
    try:
        return request.build_absolute_uri(field.url)
    except (ValueError, AttributeError):
        return ""


def _user_payload(user) -> dict:
    return {
        "id": user.pk,
        "username": user.get_username(),
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


@ensure_csrf_cookie
@require_GET
def auth_session(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "authenticated": bool(request.user.is_authenticated and request.user.is_staff),
            "user": _user_payload(request.user) if request.user.is_authenticated and request.user.is_staff else None,
        }
    )


@require_POST
def auth_login(request: HttpRequest) -> JsonResponse:
    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return JsonResponse({"detail": "Username and password are required."}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return JsonResponse({"detail": "Invalid credentials."}, status=400)
    if not user.is_staff:
        return JsonResponse({"detail": "Staff access is required."}, status=403)

    login(request, user)
    return JsonResponse({"authenticated": True, "user": _user_payload(user)})


@require_POST
@_staff_required
def auth_logout(request: HttpRequest) -> JsonResponse:
    logout(request)
    return JsonResponse({"authenticated": False})


def _category_payload(category: ContentCategory | None) -> dict | None:
    if category is None:
        return None
    return {
        "id": category.id,
        "scope": category.scope,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "is_active": category.is_active,
        "updated_at": category.updated_at.isoformat(),
    }


def _category_from_payload(value, *, scope: str) -> ContentCategory | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        category_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Category must be a numeric ID or null.") from exc
    try:
        return ContentCategory.objects.get(pk=category_id, scope=scope)
    except ContentCategory.DoesNotExist as exc:
        raise ValueError("Selected category does not exist in the required scope.") from exc


@require_http_methods(["GET", "POST"])
@_staff_required
def category_list(request: HttpRequest) -> JsonResponse:
    scope = request.GET.get("scope", "").strip()
    valid_scopes = {value for value, _ in ContentCategory.Scope.choices}
    if scope not in valid_scopes:
        return JsonResponse({"detail": "A valid category scope is required."}, status=400)

    if request.method == "GET":
        rows = list(ContentCategory.objects.filter(scope=scope).order_by("name", "id"))
        return JsonResponse({"count": len(rows), "results": [_category_payload(category) for category in rows]})

    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    name = str(payload.get("name", "")).strip()
    if not name:
        return JsonResponse({"detail": "Category name is required."}, status=400)
    category = ContentCategory(
        scope=scope,
        name=name,
        slug=str(payload.get("slug", "")).strip() or slugify(name)[:140],
        description=str(payload.get("description", "")).strip(),
        is_active=bool(payload.get("is_active", True)),
    )
    try:
        category.full_clean()
        category.save()
    except Exception as exc:
        from django.core.exceptions import ValidationError
        if isinstance(exc, ValidationError):
            return JsonResponse({"detail": exc.message_dict}, status=400)
        if isinstance(exc, IntegrityError):
            return JsonResponse({"detail": "That category slug already exists in this section."}, status=409)
        raise
    return JsonResponse(_category_payload(category), status=201)


@require_http_methods(["PATCH", "DELETE"])
@_staff_required
def category_detail(request: HttpRequest, category_id: int) -> JsonResponse:
    try:
        category = ContentCategory.objects.get(pk=category_id)
    except ContentCategory.DoesNotExist:
        return JsonResponse({"detail": "Category not found."}, status=404)

    if request.method == "DELETE":
        category.delete()
        return JsonResponse({"deleted": True})

    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    for key in {"name", "slug", "description", "is_active"}:
        if key not in payload:
            continue
        value = payload[key]
        if key == "is_active":
            value = bool(value)
        else:
            value = str(value or "").strip()
        setattr(category, key, value)
    if not category.name:
        return JsonResponse({"detail": "Category name is required."}, status=400)
    if not category.slug:
        category.slug = slugify(category.name)[:140]
    try:
        category.full_clean()
        category.save()
    except Exception as exc:
        from django.core.exceptions import ValidationError
        if isinstance(exc, ValidationError):
            return JsonResponse({"detail": exc.message_dict}, status=400)
        if isinstance(exc, IntegrityError):
            return JsonResponse({"detail": "That category slug already exists in this section."}, status=409)
        raise
    return JsonResponse(_category_payload(category))


@require_GET
@_staff_required
def dashboard(request: HttpRequest) -> JsonResponse:
    latest_discovery = DiscoveryRun.objects.order_by("-started_at", "-id").first()
    return JsonResponse(
        {
            "courses": {
                "total": Course.objects.count(),
                "active": Course.objects.filter(status=Course.Status.ACTIVE).count(),
                "customized": Course.objects.exclude(editorial_title="").count(),
            },
            "shopping": {
                "posts": ShoppingPost.objects.count(),
                "published": ShoppingPost.objects.filter(status=ShoppingPost.Status.PUBLISHED).count(),
                "products": ShoppingProduct.objects.count(),
            },
            "analytics": {
                "course_clicks": ClickEvent.objects.count(),
                "shopping_clicks": ShoppingClickEvent.objects.count(),
            },
            "publishing": {
                "queued": PublicationQueueItem.objects.filter(status=PublicationQueueItem.Status.QUEUED).count(),
                "telegram_failed": TelegramPost.objects.filter(status=TelegramPost.Status.FAILED).count(),
            },
            "media": {"assets": MediaAsset.objects.count()},
            "categories": {
                "courses": ContentCategory.objects.filter(scope=ContentCategory.Scope.COURSE).count(),
                "affiliate": ContentCategory.objects.filter(scope=ContentCategory.Scope.AFFILIATE).count(),
            },
            "discovery": {
                "latest_status": latest_discovery.status if latest_discovery else None,
                "latest_started_at": latest_discovery.started_at.isoformat() if latest_discovery else None,
            },
        }
    )


def _course_summary(course: Course) -> dict:
    return {
        "id": course.id,
        "title": course.public_title,
        "source_title": course.title,
        "provider": course.provider.name,
        "provider_slug": course.provider.slug,
        "external_id": course.external_id,
        "slug": course.slug,
        "status": course.status,
        "thumbnail_url": course.thumbnail_url,
        "category": _category_payload(course.category),
        "language": course.language,
        "short_description": course.short_description,
        "rating": str(course.rating) if course.rating is not None else None,
        "review_count": course.review_count,
        "last_checked_at": course.last_checked_at.isoformat() if course.last_checked_at else None,
        "customized": course.is_editorially_customized,
        "updated_at": course.updated_at.isoformat(),
    }


@require_GET
@_staff_required
def course_list(request: HttpRequest) -> JsonResponse:
    queryset = Course.objects.select_related("provider", "category").order_by("-updated_at", "-id")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(editorial_title__icontains=query)
            | Q(slug__icontains=query)
            | Q(external_id__icontains=query)
        )
    valid_statuses = {value for value, _ in Course.Status.choices}
    if status in valid_statuses:
        queryset = queryset.filter(status=status)

    try:
        limit = max(1, min(int(request.GET.get("limit", "50")), MAX_PAGE_SIZE))
    except ValueError:
        limit = 50
    rows = list(queryset[:limit])
    return JsonResponse({"count": len(rows), "results": [_course_summary(course) for course in rows]})


def _course_detail(request: HttpRequest, course: Course) -> dict:
    latest_prices = list(course.prices.order_by("-observed_at", "-id")[:20])
    eligibility = getattr(course, "publication_eligibility", None)
    return {
        **_course_summary(course),
        "cms": {
            "editorial_title": course.editorial_title,
            "editorial_description": course.editorial_description,
            "content": course.editorial_description,
            "short_description": course.short_description,
            "category": _category_payload(course.category),
            "language": course.language,
            "editorial_image_url": _file_url(request, course.editorial_image),
            "seo_title": course.seo_title,
            "meta_description": course.meta_description,
            "meta_keywords": course.meta_keywords,
            "social_image_url": _file_url(request, course.social_image),
        },
        "source": {
            "canonical_url": course.canonical_url,
            "thumbnail_url": course.thumbnail_url,
            "instructor_name": course.instructor_name,
            "description": course.description,
            "student_count": course.student_count,
            "duration_minutes": course.duration_minutes,
            "first_seen_at": course.first_seen_at.isoformat(),
            "last_seen_at": course.last_seen_at.isoformat(),
        },
        "prices": [
            {
                "amount": str(price.amount) if price.amount is not None else None,
                "currency": price.currency,
                "is_free": price.is_free,
                "price_type": price.price_type,
                "observed_at": price.observed_at.isoformat(),
            }
            for price in latest_prices
        ],
        "publishing": {
            "eligible": eligibility.eligible if eligibility else False,
            "score": eligibility.score if eligibility else None,
            "reasons": eligibility.reasons if eligibility else [],
            "evaluated_at": eligibility.evaluated_at.isoformat() if eligibility else None,
            "queue_count": course.publication_queue_items.count(),
            "click_count": course.click_events.count(),
        },
    }


@require_http_methods(["GET", "PATCH"])
@_staff_required
def course_detail(request: HttpRequest, course_id: int) -> JsonResponse:
    try:
        course = Course.objects.select_related("provider", "category").get(pk=course_id)
    except Course.DoesNotExist:
        return JsonResponse({"detail": "Course not found."}, status=404)

    if request.method == "GET":
        return JsonResponse(_course_detail(request, course))

    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    allowed = {"status", "slug", "editorial_title", "editorial_description", "content", "short_description", "category_id", "language", "seo_title", "meta_description", "meta_keywords"}
    for key in allowed:
        if key not in payload:
            continue
        value = payload[key]
        if key in {"editorial_description", "content"}:
            course.editorial_description = sanitize_rich_html(str(value or ""))
            continue
        if key == "category_id":
            try:
                course.category = _category_from_payload(value, scope=ContentCategory.Scope.COURSE)
            except ValueError as exc:
                return JsonResponse({"detail": str(exc)}, status=400)
            continue
        if key == "language":
            course.language = str(value or "").strip() or None
            continue
        if key == "status":
            if value not in {choice for choice, _ in Course.Status.choices}:
                return JsonResponse({"detail": "Invalid course status."}, status=400)
        else:
            value = str(value or "").strip()
        setattr(course, key, value)

    try:
        course.full_clean(exclude=("editorial_image", "social_image"))
        course.save()
    except (IntegrityError, Exception) as exc:
        if isinstance(exc, IntegrityError):
            return JsonResponse({"detail": "The requested slug conflicts with another course."}, status=409)
        from django.core.exceptions import ValidationError
        if isinstance(exc, ValidationError):
            return JsonResponse({"detail": exc.message_dict}, status=400)
        raise
    return JsonResponse(_course_detail(request, course))


def _shopping_post_summary(post: ShoppingPost) -> dict:
    return {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "post_type": post.post_type,
        "status": post.status,
        "category": _category_payload(post.category),
        "language": post.language,
        "short_description": post.excerpt,
        "is_featured": post.is_featured,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "updated_at": post.updated_at.isoformat(),
        "product_count": post.products.count(),
    }


def _product_payload(request: HttpRequest, product: ShoppingProduct) -> dict:
    return {
        "id": product.id,
        "position": product.position,
        "name": product.name,
        "title": product.name,
        "slug": product.slug,
        "image_url": _file_url(request, product.image),
        "short_description": product.short_description,
        "content": product.content,
        "category": _category_payload(product.category),
        "language": product.language,
        "affiliate_url": product.affiliate_url,
        "displayed_price": str(product.displayed_price) if product.displayed_price is not None else "",
        "original_price": str(product.original_price) if product.original_price is not None else "",
        "currency": product.currency,
        "badge": product.badge,
        "pros": product.pros,
        "cons": product.cons,
        "is_active": product.is_active,
        "expires_at": product.expires_at.isoformat() if product.expires_at else None,
    }


def _shopping_post_detail(request: HttpRequest, post: ShoppingPost) -> dict:
    return {
        **_shopping_post_summary(post),
        "excerpt": post.excerpt,
        "short_description": post.excerpt,
        "body": post.body,
        "content": post.body,
        "cover_image_url": _file_url(request, post.cover_image),
        "seo_title": post.seo_title,
        "meta_description": post.meta_description,
        "meta_keywords": post.meta_keywords,
        "products": [_product_payload(request, product) for product in post.products.order_by("position", "id")],
    }


@require_http_methods(["GET", "POST"])
@_staff_required
def shopping_post_list(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        queryset = ShoppingPost.objects.select_related("category").annotate(_product_count=Count("products")).order_by("-updated_at", "-id")
        query = request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(slug__icontains=query))
        rows = list(queryset[:MAX_PAGE_SIZE])
        return JsonResponse({"count": len(rows), "results": [_shopping_post_summary(post) for post in rows]})

    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    title = str(payload.get("title", "")).strip()
    if not title:
        return JsonResponse({"detail": "Title is required."}, status=400)
    requested_slug = str(payload.get("slug", "")).strip()
    post = ShoppingPost(title=title, slug=requested_slug or slugify(title)[:320])
    post.post_type = str(payload.get("post_type", ShoppingPost.PostType.TOP_LIST))
    post.excerpt = str(payload.get("short_description", payload.get("excerpt", ""))).strip()
    post.body = sanitize_rich_html(str(payload.get("content", payload.get("body", "")) or ""))
    post.language = str(payload.get("language", "")).strip() or None
    try:
        post.category = _category_from_payload(payload.get("category_id"), scope=ContentCategory.Scope.AFFILIATE)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    try:
        post.full_clean()
        post.save()
    except Exception as exc:
        from django.core.exceptions import ValidationError
        if isinstance(exc, ValidationError):
            return JsonResponse({"detail": exc.message_dict}, status=400)
        if isinstance(exc, IntegrityError):
            return JsonResponse({"detail": "A shopping post already uses that slug."}, status=409)
        raise
    return JsonResponse(_shopping_post_detail(request, post), status=201)


@require_http_methods(["GET", "PATCH", "DELETE"])
@_staff_required
def shopping_post_detail(request: HttpRequest, post_id: int) -> JsonResponse:
    try:
        post = ShoppingPost.objects.select_related("category").prefetch_related("products__category").get(pk=post_id)
    except ShoppingPost.DoesNotExist:
        return JsonResponse({"detail": "Shopping post not found."}, status=404)

    if request.method == "GET":
        return JsonResponse(_shopping_post_detail(request, post))
    if request.method == "DELETE":
        if post.status == ShoppingPost.Status.PUBLISHED:
            return JsonResponse({"detail": "Archive a published post before deleting it."}, status=409)
        post.delete()
        return JsonResponse({"deleted": True})

    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    fields = {"title", "slug", "post_type", "status", "excerpt", "short_description", "body", "content", "category_id", "language", "seo_title", "meta_description", "meta_keywords", "is_featured"}
    for key in fields:
        if key not in payload:
            continue
        value = payload[key]
        if key in {"body", "content"}:
            post.body = sanitize_rich_html(str(value or ""))
            continue
        if key in {"excerpt", "short_description"}:
            post.excerpt = str(value or "").strip()
            continue
        if key == "category_id":
            try:
                post.category = _category_from_payload(value, scope=ContentCategory.Scope.AFFILIATE)
            except ValueError as exc:
                return JsonResponse({"detail": str(exc)}, status=400)
            continue
        if key == "language":
            post.language = str(value or "").strip() or None
            continue
        if key == "is_featured":
            value = bool(value)
        elif key == "post_type":
            if value not in {choice for choice, _ in ShoppingPost.PostType.choices}:
                return JsonResponse({"detail": "Invalid post type."}, status=400)
        elif key == "status":
            if value not in {choice for choice, _ in ShoppingPost.Status.choices}:
                return JsonResponse({"detail": "Invalid post status."}, status=400)
        else:
            value = str(value or "").strip()
        setattr(post, key, value)

    try:
        post.full_clean(exclude=("cover_image",))
        post.save()
    except Exception as exc:
        from django.core.exceptions import ValidationError
        if isinstance(exc, ValidationError):
            return JsonResponse({"detail": exc.message_dict}, status=400)
        if isinstance(exc, IntegrityError):
            return JsonResponse({"detail": "A shopping post already uses that slug."}, status=409)
        raise
    return JsonResponse(_shopping_post_detail(request, post))


def _decimal_or_none(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Invalid price value.") from exc


@require_POST
@_staff_required
def shopping_product_create(request: HttpRequest, post_id: int) -> JsonResponse:
    try:
        post = ShoppingPost.objects.get(pk=post_id)
    except ShoppingPost.DoesNotExist:
        return JsonResponse({"detail": "Shopping post not found."}, status=404)
    try:
        payload = _json_body(request)
        product = ShoppingProduct(
            post=post,
            position=int(payload.get("position", post.products.count() + 1)),
            name=str(payload.get("name", payload.get("title", ""))).strip(),
            slug=(str(payload.get("slug", "")).strip() or slugify(str(payload.get("name", payload.get("title", ""))).strip())[:220]),
            short_description=str(payload.get("short_description", "")).strip(),
            content=sanitize_rich_html(str(payload.get("content", "") or "")),
            language=str(payload.get("language", "")).strip() or None,
            affiliate_url=str(payload.get("affiliate_url", "")).strip(),
            displayed_price=_decimal_or_none(payload.get("displayed_price")),
            original_price=_decimal_or_none(payload.get("original_price")),
            currency=str(payload.get("currency", "PHP")).strip(),
            badge=str(payload.get("badge", "")).strip(),
            pros=str(payload.get("pros", "")).strip(),
            cons=str(payload.get("cons", "")).strip(),
            is_active=bool(payload.get("is_active", True)),
        )
        product.category = _category_from_payload(payload.get("category_id"), scope=ContentCategory.Scope.AFFILIATE)
        product.full_clean(exclude=("image",))
        product.save()
    except (ValueError, TypeError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    except Exception as exc:
        from django.core.exceptions import ValidationError
        if isinstance(exc, ValidationError):
            return JsonResponse({"detail": exc.message_dict}, status=400)
        if isinstance(exc, IntegrityError):
            return JsonResponse({"detail": "Product position or slug already exists in this post."}, status=409)
        raise
    return JsonResponse(_product_payload(request, product), status=201)


@require_http_methods(["PATCH", "DELETE"])
@_staff_required
def shopping_product_detail(request: HttpRequest, product_id: int) -> JsonResponse:
    try:
        product = ShoppingProduct.objects.select_related("post", "category").get(pk=product_id)
    except ShoppingProduct.DoesNotExist:
        return JsonResponse({"detail": "Shopping product not found."}, status=404)
    if request.method == "DELETE":
        product.delete()
        return JsonResponse({"deleted": True})

    try:
        payload = _json_body(request)
        for key in {"position", "name", "title", "slug", "short_description", "content", "category_id", "language", "affiliate_url", "currency", "badge", "pros", "cons", "is_active"}:
            if key not in payload:
                continue
            value = payload[key]
            if key == "position":
                value = int(value)
            elif key == "is_active":
                value = bool(value)
            elif key == "title":
                product.name = str(value or "").strip()
                continue
            elif key == "content":
                value = sanitize_rich_html(str(value or ""))
            elif key == "category_id":
                product.category = _category_from_payload(value, scope=ContentCategory.Scope.AFFILIATE)
                continue
            elif key == "language":
                product.language = str(value or "").strip() or None
                continue
            else:
                value = str(value or "").strip()
            setattr(product, key, value)
        if "displayed_price" in payload:
            product.displayed_price = _decimal_or_none(payload.get("displayed_price"))
        if "original_price" in payload:
            product.original_price = _decimal_or_none(payload.get("original_price"))
        product.full_clean(exclude=("image",))
        product.save()
    except (ValueError, TypeError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    except Exception as exc:
        from django.core.exceptions import ValidationError
        if isinstance(exc, ValidationError):
            return JsonResponse({"detail": exc.message_dict}, status=400)
        if isinstance(exc, IntegrityError):
            return JsonResponse({"detail": "Product position or slug already exists in this post."}, status=409)
        raise
    return JsonResponse(_product_payload(request, product))


def _validate_image_upload(upload) -> str | None:
    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return "Unsupported image extension."
    content_type = (getattr(upload, "content_type", "") or "").lower()
    if content_type and content_type not in ALLOWED_IMAGE_MIME_TYPES:
        return "Unsupported image content type."
    if upload.size > 8 * 1024 * 1024:
        return "Image must be 8 MB or smaller."
    return None


def _save_image_field(request: HttpRequest, obj, field_name: str) -> JsonResponse:
    upload = request.FILES.get("upload") or request.FILES.get("file")
    if upload is None:
        return JsonResponse({"detail": "Image upload is required."}, status=400)
    error = _validate_image_upload(upload)
    if error:
        return JsonResponse({"detail": error}, status=400)
    field = getattr(obj, field_name)
    if field:
        field.delete(save=False)
    field.save(upload.name, upload, save=False)
    obj.save()
    return JsonResponse({"url": _file_url(request, getattr(obj, field_name))})


@require_POST
@_staff_required
def course_image_upload(request: HttpRequest, course_id: int, kind: str) -> JsonResponse:
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return JsonResponse({"detail": "Course not found."}, status=404)
    field_name = {"editorial": "editorial_image", "social": "social_image"}.get(kind)
    if not field_name:
        return JsonResponse({"detail": "Invalid course image kind."}, status=400)
    return _save_image_field(request, course, field_name)


@require_POST
@_staff_required
def shopping_post_cover_upload(request: HttpRequest, post_id: int) -> JsonResponse:
    try:
        post = ShoppingPost.objects.get(pk=post_id)
    except ShoppingPost.DoesNotExist:
        return JsonResponse({"detail": "Shopping post not found."}, status=404)
    return _save_image_field(request, post, "cover_image")


@require_POST
@_staff_required
def shopping_product_image_upload(request: HttpRequest, product_id: int) -> JsonResponse:
    try:
        product = ShoppingProduct.objects.get(pk=product_id)
    except ShoppingProduct.DoesNotExist:
        return JsonResponse({"detail": "Shopping product not found."}, status=404)
    return _save_image_field(request, product, "image")


@require_http_methods(["GET", "POST"])
@_staff_required
def media_list(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        rows = list(MediaAsset.objects.select_related("uploaded_by")[:MAX_PAGE_SIZE])
        return JsonResponse(
            {
                "count": len(rows),
                "results": [
                    {
                        "id": asset.id,
                        "url": _file_url(request, asset.file),
                        "name": Path(asset.file.name).name,
                        "title": asset.title,
                        "alt_text": asset.alt_text,
                        "content_type": asset.content_type,
                        "size_bytes": asset.size_bytes,
                        "created_at": asset.created_at.isoformat(),
                    }
                    for asset in rows
                ],
            }
        )

    upload = request.FILES.get("upload") or request.FILES.get("file")
    if upload is None:
        return JsonResponse({"error": {"message": "Image upload is required."}}, status=400)
    error = _validate_image_upload(upload)
    if error:
        return JsonResponse({"error": {"message": error}}, status=400)

    asset = MediaAsset.objects.create(
        file=upload,
        title=request.POST.get("title", "").strip(),
        alt_text=request.POST.get("alt_text", "").strip(),
        content_type=(getattr(upload, "content_type", "") or "")[:100],
        size_bytes=upload.size,
        uploaded_by=request.user,
    )
    return JsonResponse({"url": _file_url(request, asset.file), "id": asset.id}, status=201)


@require_http_methods(["DELETE"])
@_staff_required
def media_detail(request: HttpRequest, asset_id: int) -> JsonResponse:
    try:
        asset = MediaAsset.objects.get(pk=asset_id)
    except MediaAsset.DoesNotExist:
        return JsonResponse({"detail": "Media asset not found."}, status=404)
    storage = asset.file.storage
    name = asset.file.name
    asset.delete()
    if name and storage.exists(name):
        storage.delete(name)
    return JsonResponse({"deleted": True})
