from django.urls import path

from . import public_api

app_name = "courses"

urlpatterns = [
    path("", public_api.public_course_list, name="public-course-list"),
    path("sitemap/", public_api.public_course_sitemap, name="public-course-sitemap"),
    path(
        "<slug:provider_slug>/<slug:course_slug>/",
        public_api.public_course_detail,
        name="public-course-detail",
    ),
]
