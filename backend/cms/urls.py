from django.urls import path

from . import api

app_name = "cms-admin"

urlpatterns = [
    path("auth/session/", api.auth_session, name="auth-session"),
    path("auth/login/", api.auth_login, name="auth-login"),
    path("auth/logout/", api.auth_logout, name="auth-logout"),
    path("dashboard/", api.dashboard, name="dashboard"),
    path("categories/", api.category_list, name="category-list"),
    path("categories/<int:category_id>/", api.category_detail, name="category-detail"),
    path("courses/", api.course_list, name="course-list"),
    path("courses/<int:course_id>/", api.course_detail, name="course-detail"),
    path("courses/<int:course_id>/images/<str:kind>/", api.course_image_upload, name="course-image-upload"),
    path("shop/posts/", api.shopping_post_list, name="shopping-post-list"),
    path("shop/posts/<int:post_id>/", api.shopping_post_detail, name="shopping-post-detail"),
    path("shop/posts/<int:post_id>/cover/", api.shopping_post_cover_upload, name="shopping-post-cover-upload"),
    path("shop/posts/<int:post_id>/products/", api.shopping_product_create, name="shopping-product-create"),
    path("shop/products/<int:product_id>/", api.shopping_product_detail, name="shopping-product-detail"),
    path("shop/products/<int:product_id>/image/", api.shopping_product_image_upload, name="shopping-product-image-upload"),
    path("media/", api.media_list, name="media-list"),
    path("media/<int:asset_id>/", api.media_detail, name="media-detail"),
]
