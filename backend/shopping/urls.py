from django.urls import path

from . import public_api

app_name = "shopping"

urlpatterns = [
    path("", public_api.public_post_list, name="public-post-list"),
    path("sitemap/", public_api.public_post_sitemap, name="public-post-sitemap"),
    path("<slug:post_slug>/", public_api.public_post_detail, name="public-post-detail"),
]
