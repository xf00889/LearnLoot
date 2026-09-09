"""URL configuration for the LearnLoot Django backend."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/public/courses/", include("courses.urls")),
    path("api/public/shop/", include("shopping.urls")),
    path("go/shop/", include("shopping.outbound_urls")),
    path("go/", include("tracking.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
