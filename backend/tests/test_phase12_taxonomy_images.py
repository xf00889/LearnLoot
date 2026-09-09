import json
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from cms.models import ContentCategory
from courses.models import Course
from discovery.contracts import NormalizedCourse
from discovery.services import upsert_course
from pricing.models import CoursePrice
from providers.models import Provider
from publishing.models import DealEligibility
from shopping.models import ShoppingPost, ShoppingProduct


@pytest.fixture
def provider(db):
    return Provider.objects.create(name="Udemy", slug="udemy", status=Provider.Status.ACTIVE)


@pytest.fixture
def staff_client(db):
    user = get_user_model().objects.create_user(username="editor12", password="secret-pass", is_staff=True)
    client = Client()
    assert client.login(username="editor12", password="secret-pass")
    return client


def normalized_course(*, thumbnail_url="https://img-c.udemycdn.com/course/480x270/original.jpg", title="Automation Course"):
    return NormalizedCourse(
        external_id="phase12-auto",
        title=title,
        canonical_url="https://www.udemy.com/course/phase12-auto/",
        source_url="https://www.udemy.com/courses/free/",
        source_type="udemy_free_catalog_scrapy",
        thumbnail_url=thumbnail_url,
        instructor_name="Example Instructor",
        rating=Decimal("4.60"),
        review_count=1200,
        student_count=None,
        duration_minutes=None,
        description="Scraped short provider description.",
        price_amount=Decimal("0.00"),
        currency="USD",
        is_free=True,
        price_type="free",
    )


@pytest.mark.django_db
def test_category_crud_is_manual_and_scoped(staff_client):
    course_response = staff_client.post(
        "/api/admin/categories/?scope=course",
        data=json.dumps({"name": "Development", "slug": "development"}),
        content_type="application/json",
    )
    affiliate_response = staff_client.post(
        "/api/admin/categories/?scope=affiliate",
        data=json.dumps({"name": "Home Office", "slug": "home-office"}),
        content_type="application/json",
    )

    assert course_response.status_code == 201
    assert affiliate_response.status_code == 201
    assert course_response.json()["scope"] == ContentCategory.Scope.COURSE
    assert affiliate_response.json()["scope"] == ContentCategory.Scope.AFFILIATE
    assert ContentCategory.objects.count() == 2
    assert staff_client.get("/api/admin/categories/?scope=course").json()["count"] == 1
    assert staff_client.get("/api/admin/categories/?scope=affiliate").json()["count"] == 1


@pytest.mark.django_db
def test_automated_course_category_starts_null_and_manual_taxonomy_survives_rediscovery(provider):
    first = upsert_course(provider, normalized_course())
    course = first.course
    assert course.category_id is None
    assert course.language is None

    category = ContentCategory.objects.create(scope=ContentCategory.Scope.COURSE, name="Programming", slug="programming")
    course.category = category
    course.language = "English"
    course.short_description = "Manual short description"
    course.editorial_description = "<p>Manual rich content</p>"
    course.save()

    upsert_course(provider, normalized_course(title="Updated scraped title", thumbnail_url=""))
    course.refresh_from_db()

    assert course.title == "Updated scraped title"
    assert course.category == category
    assert course.language == "English"
    assert course.short_description == "Manual short description"
    assert course.editorial_description == "<p>Manual rich content</p>"
    assert course.thumbnail_url == "https://img-c.udemycdn.com/course/480x270/original.jpg"


@pytest.mark.django_db
def test_course_admin_accepts_nullable_category_language_and_content_alias(staff_client, provider):
    course = upsert_course(provider, normalized_course()).course
    category = ContentCategory.objects.create(scope=ContentCategory.Scope.COURSE, name="Data", slug="data")

    response = staff_client.patch(
        f"/api/admin/courses/{course.id}/",
        data=json.dumps({
            "content": "<h2>Edited content</h2><script>bad()</script>",
            "short_description": "A useful short description",
            "category_id": category.id,
            "language": "English",
        }),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cms"]["category"]["slug"] == "data"
    assert payload["cms"]["language"] == "English"
    assert payload["cms"]["short_description"] == "A useful short description"
    assert "<script" not in payload["cms"]["content"]

    cleared = staff_client.patch(
        f"/api/admin/courses/{course.id}/",
        data=json.dumps({"category_id": None, "language": ""}),
        content_type="application/json",
    )
    assert cleared.status_code == 200
    course.refresh_from_db()
    assert course.category_id is None
    assert course.language is None


@pytest.mark.django_db
def test_course_admin_rejects_affiliate_category(staff_client, provider):
    course = upsert_course(provider, normalized_course()).course
    wrong = ContentCategory.objects.create(scope=ContentCategory.Scope.AFFILIATE, name="Wrong", slug="wrong")
    response = staff_client.patch(
        f"/api/admin/courses/{course.id}/",
        data=json.dumps({"category_id": wrong.id}),
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_affiliate_post_and_product_support_manual_category_language_and_content(staff_client):
    category = ContentCategory.objects.create(scope=ContentCategory.Scope.AFFILIATE, name="Tech", slug="tech")
    created = staff_client.post(
        "/api/admin/shop/posts/",
        data=json.dumps({
            "title": "Top accessories",
            "slug": "top-accessories",
            "short_description": "Short affiliate intro",
            "content": "<p>Long editorial content</p>",
            "category_id": category.id,
            "language": "English",
        }),
        content_type="application/json",
    )
    assert created.status_code == 201
    post = ShoppingPost.objects.get()
    assert post.category == category
    assert post.language == "English"
    assert post.excerpt == "Short affiliate intro"

    product = staff_client.post(
        f"/api/admin/shop/posts/{post.id}/products/",
        data=json.dumps({
            "position": 1,
            "name": "Mechanical Keyboard",
            "slug": "mechanical-keyboard",
            "affiliate_url": "https://shopee.ph/example",
            "short_description": "Compact keyboard",
            "content": "<p>Detailed product notes</p><script>bad()</script>",
            "category_id": category.id,
            "language": "English",
        }),
        content_type="application/json",
    )
    assert product.status_code == 201
    row = ShoppingProduct.objects.get()
    assert row.category == category
    assert row.language == "English"
    assert "Detailed product notes" in row.content
    assert "<script" not in row.content


@pytest.mark.django_db
def test_affiliate_post_creation_can_add_first_affiliate_link_atomically(staff_client):
    response = staff_client.post(
        "/api/admin/shop/posts/",
        data=json.dumps({
            "title": "Mechanical keyboard deal",
            "affiliate_url": "https://shopee.ph/mechanical-keyboard",
        }),
        content_type="application/json",
    )

    assert response.status_code == 201
    post = ShoppingPost.objects.get()
    product = post.products.get()
    assert product.position == 1
    assert product.name == post.title
    assert product.affiliate_url == "https://shopee.ph/mechanical-keyboard"
    assert response.json()["product_count"] == 1

    rejected = staff_client.post(
        "/api/admin/shop/posts/",
        data=json.dumps({"title": "Invalid link", "affiliate_url": "http://unsafe.example/item"}),
        content_type="application/json",
    )
    assert rejected.status_code == 400
    assert ShoppingPost.objects.count() == 1


@pytest.mark.django_db
def test_public_course_search_payload_carries_thumbnail_taxonomy_and_language(provider, settings):
    settings.LEARNLOOT_PUBLIC_BASE_URL = "https://learnloot.test"
    now = timezone.now()
    category = ContentCategory.objects.create(scope=ContentCategory.Scope.COURSE, name="Python", slug="python")
    course = Course.objects.create(
        provider=provider,
        external_id="public-phase12",
        title="Public Course",
        slug="public-course",
        canonical_url="https://www.udemy.com/course/public-course/",
        thumbnail_url="https://img-c.udemycdn.com/course/480x270/public.jpg",
        category=category,
        language="English",
        short_description="Short public copy",
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

    response = Client().get("/api/public/courses/?q=Python")

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["thumbnail_url"].endswith("/public.jpg")
    assert row["category"] == {"name": "Python", "slug": "python"}
    assert row["language"] == "English"
    assert row["short_description"] == "Short public copy"


def test_phase12_frontend_has_nested_course_affiliate_categories_and_course_images():
    root = Path(__file__).resolve().parents[2]
    shell = (root / "frontend" / "src" / "components" / "admin" / "admin-shell.tsx").read_text(encoding="utf-8")
    course_categories = (root / "frontend" / "src" / "app" / "admin" / "courses" / "categories" / "page.tsx").read_text(encoding="utf-8")
    affiliate_categories = (root / "frontend" / "src" / "app" / "admin" / "shop" / "categories" / "page.tsx").read_text(encoding="utf-8")
    course_list = (root / "frontend" / "src" / "app" / "courses" / "page.tsx").read_text(encoding="utf-8")
    course_card = (root / "frontend" / "src" / "components" / "course-card.tsx").read_text(encoding="utf-8")
    admin_course_list = (root / "frontend" / "src" / "app" / "admin" / "courses" / "page.tsx").read_text(encoding="utf-8")
    affiliate_editor = (root / "frontend" / "src" / "app" / "admin" / "shop" / "[id]" / "page.tsx").read_text(encoding="utf-8")
    shopping_grid = (root / "frontend" / "src" / "components" / "shopping-post-grid.tsx").read_text(encoding="utf-8")

    assert 'href: "/admin/courses/categories"' in shell
    assert 'href: "/admin/shop/categories"' in shell
    assert "CategoryManager" in course_categories
    assert "CategoryManager" in affiliate_categories
    assert "CourseCard" in course_list
    assert "course.thumbnail_url" in course_card
    assert "row.thumbnail_url" in admin_course_list
    assert "ClientRichTextEditor value={product.content}" in affiliate_editor
    assert "ClientRichTextEditor value={draftProduct.content}" in affiliate_editor
    assert "post.category.name" in shopping_grid
    assert "post.language" in shopping_grid
