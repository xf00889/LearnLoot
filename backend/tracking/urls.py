from django.urls import path

from .views import outbound_redirect

app_name = "tracking"

urlpatterns = [
    path(
        "<slug:provider_slug>/<slug:course_slug>/",
        outbound_redirect,
        name="outbound-redirect",
    ),
]
