"""URL configuration for the LearnLoot Django backend."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import health, live, ready

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/admin/", include("cms.urls")),
    path("api/health/", health, name="health"),
    path("api/health/live/", live, name="health-live"),
    path("api/health/ready/", ready, name="health-ready"),
    path("api/public/courses/", include("courses.urls")),
    path("api/public/shop/", include("shopping.urls")),
    path("go/shop/", include("shopping.outbound_urls")),
    path("go/", include("tracking.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
