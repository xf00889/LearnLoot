from django.urls import path

from .views import shopping_outbound_redirect

app_name = "shopping-outbound"

urlpatterns = [
    path(
        "<slug:post_slug>/<slug:product_slug>/",
        shopping_outbound_redirect,
        name="shopping-outbound-redirect",
    ),
]
