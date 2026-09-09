import json
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone

from courses.models import Course
from pricing.models import CoursePrice
from providers.models import Provider
from publishing.models import DealEligibility
from shopping.models import ShoppingPost
from cms.models import MediaAsset


@pytest.fixture
def provider(db):
    return Provider.objects.create(name="Udemy", slug="udemy", status=Provider.Status.ACTIVE)


@pytest.fixture
def staff_client(db):
    user = get_user_model().objects.create_user(username="editor", password="secret-pass", is_staff=True)
    client = Client()
    assert client.login(username="editor", password="secret-pass")
    return client


def make_course(provider):
    now = timezone.now()
    course = Course.objects.create(
        provider=provider,
        external_id="cms-course",
        title="Scraped title",
        slug="cms-course",
        canonical_url="https://www.udemy.com/course/cms-course/",
        description="Scraped description",
        rating=Decimal("4.70"),
        review_count=500,
        last_seen_at=now,
        last_checked_at=now,
    )
    price = CoursePrice.objects.create(
        course=course,
        amount=Decimal("0.00"),
        currency="USD",
        is_free=True,
        price_type="free",
        observed_at=now,
        source_url=course.canonical_url,
    )
    DealEligibility.objects.create(course=course, latest_price=price, score=90, eligible=True, reasons=[], evaluated_at=now)
    return course


@pytest.mark.django_db
def test_custom_admin_auth_requires_staff():
    client = Client()
    assert client.get("/api/admin/dashboard/").status_code == 401

    user = get_user_model().objects.create_user(username="plain", password="pw")
    client.force_login(user)
    assert client.get("/api/admin/dashboard/").status_code == 403


@pytest.mark.django_db
def test_custom_admin_login_and_session_endpoint():
    get_user_model().objects.create_user(username="editor", password="secret-pass", is_staff=True)
    client = Client()
    session = client.get("/api/admin/auth/session/")
    assert session.status_code == 200
    assert session.json()["authenticated"] is False

    response = client.post(
        "/api/admin/auth/login/",
        data=json.dumps({"username": "editor", "password": "secret-pass"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert client.get("/api/admin/auth/session/").json()["user"]["username"] == "editor"


@pytest.mark.django_db
def test_course_cms_update_sanitizes_rich_html_and_preserves_scraped_source(staff_client, provider):
    course = make_course(provider)
    payload = {
        "editorial_title": "Editor title",
        "editorial_description": '<h2>Useful</h2><script>alert(1)</script><p><a href="javascript:alert(2)">Read</a></p>',
        "seo_title": "Editor SEO title",
        "meta_description": "Editor meta description",
        "meta_keywords": "python, free course",
    }
    response = staff_client.patch(
        f"/api/admin/courses/{course.id}/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    course.refresh_from_db()
    assert course.title == "Scraped title"
    assert course.description == "Scraped description"
    assert course.editorial_title == "Editor title"
    assert "<script" not in course.editorial_description
    assert "javascript:" not in course.editorial_description
    assert "<h2>Useful</h2>" in course.editorial_description


@pytest.mark.django_db
def test_shopping_body_is_sanitized_from_custom_admin(staff_client):
    post = ShoppingPost.objects.create(title="Top products", slug="top-products")
    response = staff_client.patch(
        f"/api/admin/shop/posts/{post.id}/",
        data=json.dumps({"body": '<p>Safe</p><img src="https://example.test/a.jpg" onerror="bad()"><script>bad()</script>'}),
        content_type="application/json",
    )
    assert response.status_code == 200
    post.refresh_from_db()
    assert "<p>Safe</p>" in post.body
    assert "onerror" not in post.body
    assert "<script" not in post.body


@pytest.mark.django_db
def test_media_library_upload_is_staff_only_and_privacy_minimized(staff_client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    upload = SimpleUploadedFile("editor.webp", b"fake-image-bytes", content_type="image/webp")
    response = staff_client.post("/api/admin/media/", {"upload": upload, "title": "Editor image", "alt_text": "Useful alt"})
    assert response.status_code == 201
    asset = MediaAsset.objects.get()
    assert asset.title == "Editor image"
    assert asset.alt_text == "Useful alt"
    assert asset.uploaded_by.username == "editor"
    fields = {field.name for field in MediaAsset._meta.fields}
    assert "ip_address" not in fields
    assert "user_agent" not in fields


@pytest.mark.django_db
def test_dashboard_and_course_list_work_for_staff(staff_client, provider):
    course = make_course(provider)
    dashboard = staff_client.get("/api/admin/dashboard/")
    assert dashboard.status_code == 200
    assert dashboard.json()["courses"]["total"] == 1
    listing = staff_client.get("/api/admin/courses/")
    assert listing.status_code == 200
    assert listing.json()["results"][0]["id"] == course.id


def test_phase11_frontend_custom_admin_and_editor_foundation_are_present():
    root = Path(__file__).resolve().parents[2]
    package = (root / "frontend" / "package.json").read_text(encoding="utf-8")
    admin_layout = (root / "frontend" / "src" / "app" / "admin" / "layout.tsx").read_text(encoding="utf-8")
    course_editor = (root / "frontend" / "src" / "app" / "admin" / "courses" / "[id]" / "page.tsx").read_text(encoding="utf-8")
    shopping_editor = (root / "frontend" / "src" / "app" / "admin" / "shop" / "[id]" / "page.tsx").read_text(encoding="utf-8")
    rich_editor = (root / "frontend" / "src" / "components" / "admin" / "rich-text-editor.tsx").read_text(encoding="utf-8")
    theme = (root / "frontend" / "src" / "components" / "admin" / "admin-theme-provider.tsx").read_text(encoding="utf-8")
    urls = (root / "backend" / "config" / "urls.py").read_text(encoding="utf-8")

    assert '"@mui/material": "7.3.11"' in package
    assert '"ckeditor5": "48.5.0"' in package
    assert "robots: { index: false" in admin_layout
    assert "ClientRichTextEditor" in course_editor
    assert "ClientRichTextEditor" in shopping_editor
    assert "SimpleUploadAdapter" in rich_editor
    assert 'licenseKey' in rich_editor and '"GPL"' in rich_editor
    assert "borderRadius: 4" in theme
    assert 'path("django-admin/", admin.site.urls)' in urls
    assert 'path("api/admin/", include("cms.urls"))' in urls
