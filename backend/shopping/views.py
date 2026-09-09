from __future__ import annotations

from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import ShoppingPost, ShoppingProduct
from .services import ShoppingDestinationError, record_shopping_click_event, resolve_shopping_destination


def _public_product_or_404(post_slug: str, product_slug: str) -> ShoppingProduct:
    now = timezone.now()
    try:
        product = (
            ShoppingProduct.objects.select_related("post")
            .filter(
                post__slug=post_slug,
                post__status=ShoppingPost.Status.PUBLISHED,
                post__published_at__isnull=False,
                post__published_at__lte=now,
                slug=product_slug,
                is_active=True,
            )
            .get()
        )
    except ShoppingProduct.DoesNotExist as exc:
        raise Http404("Shopping product is not public") from exc

    if product.expires_at is not None and product.expires_at <= now:
        raise Http404("Shopping product is expired")
    return product


@require_GET
def shopping_outbound_redirect(request: HttpRequest, post_slug: str, product_slug: str) -> HttpResponseRedirect:
    product = _public_product_or_404(post_slug, product_slug)
    try:
        destination = resolve_shopping_destination(product)
    except ShoppingDestinationError as exc:
        raise Http404("Shopping destination unavailable") from exc

    # Best-effort, privacy-minimized analytics. No IP/user-agent is persisted.
    record_shopping_click_event(request=request, product=product)

    response = HttpResponseRedirect(destination.url)
    response["Cache-Control"] = "no-store, private"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
