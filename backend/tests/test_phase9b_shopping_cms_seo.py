from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib import admin
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.utils import timezone

from courses.admin import CourseAdmin
from courses.models import Course
from discovery.contracts import NormalizedCourse
from discovery.services import upsert_course
from pricing.models import CoursePrice
from providers.models import Provider
from publishing.models import DealEligibility
from shopping.admin import ShoppingPostAdmin
from shopping.models import ShoppingClickEvent, ShoppingPost, ShoppingProduct


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def provider(db):
    return Provider.objects.create(name="Udemy", slug="udemy", status=Provider.Status.ACTIVE)


def make_public_course(provider, *, slug="python-course"):
    now = timezone.now()
    course = Course.objects.create(
        provider=provider,
        external_id=slug,
        title="Scraped Python Course",
        slug=slug,
        canonical_url=f"https://www.udemy.com/course/{slug}/",
        thumbnail_url="https://example.test/raw.jpg",
        instructor_name="Provider Instructor",
        rating=Decimal("4.70"),
        review_count=1500,
        description="Scraped provider description.",
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
    DealEligibility.objects.create(
        course=course,
        latest_price=price,
        score=91,
        eligible=True,
        reasons=[],
        evaluated_at=now,
    )
    return course


def make_post(*, status=ShoppingPost.Status.PUBLISHED, post_type=ShoppingPost.PostType.TOP_LIST):
    return ShoppingPost.objects.create(
        post_type=post_type,
        title="10 Useful Desk Accessories",
        slug="useful-desk-accessories",
        excerpt="Original LearnLoot notes for practical desk accessories.",
        body="Choose based on your desk size and daily workflow.",
        seo_title="10 Useful Desk Accessories in the Philippines",
        meta_description="Compare ten useful desk accessories with original LearnLoot buying notes.",
        meta_keywords="desk accessories philippines, shopee desk deals",
        status=status,
    )


def make_product(post, *, slug="desk-lamp", active=True, expires_at=None):
    return ShoppingProduct.objects.create(
        post=post,
        position=1,
        name="Adjustable Desk Lamp",
        slug=slug,
        short_description="A compact lamp selected for small workspaces.",
        affiliate_url="https://shopee.ph/example-affiliate-link",
        displayed_price=Decimal("499.00"),
        original_price=Decimal("699.00"),
        currency="php",
        badge="Budget pick",
        pros="Compact\nAdjustable",
        cons="No battery",
        is_active=active,
        expires_at=expires_at,
    )


@pytest.mark.django_db
@override_settings(LEARNLOOT_PUBLIC_BASE_URL="https://learnloot.test")
def test_shopping_api_exposes_published_editorial_content_without_raw_affiliate_url():
    post = make_post()
    product = make_product(post)

    response = Client().get(f"/api/public/shop/{post.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == post.title
    assert payload["seo"]["title"] == post.seo_title
    assert payload["affiliate_disclosure"].startswith("This page contains affiliate links")
    assert payload["products"][0]["name"] == product.name
    assert payload["products"][0]["outbound_url"].endswith(
        f"/go/shop/{post.slug}/{product.slug}/"
    )
    serialized = str(payload)
    assert "affiliate_url" not in serialized
    assert product.affiliate_url not in serialized


@pytest.mark.django_db
def test_draft_shopping_posts_are_not_public():
    post = make_post(status=ShoppingPost.Status.DRAFT)
    make_product(post)

    assert Client().get("/api/public/shop/").json()["results"] == []
    assert Client().get(f"/api/public/shop/{post.slug}/").status_code == 404


@pytest.mark.django_db
@override_settings(LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS=0)
def test_shopee_redirect_records_separate_privacy_minimized_click():
    post = make_post()
    product = make_product(post)

    response = Client().get(
        f"/go/shop/{post.slug}/{product.slug}/",
        {"source": "top list", "campaign": "launch"},
    )

    assert response.status_code == 302
    assert response["Location"] == product.affiliate_url
    assert response["X-Robots-Tag"] == "noindex, nofollow"
    event = ShoppingClickEvent.objects.get()
    assert event.product == product
    assert event.source == "top-list"
    assert event.campaign == "launch"
    fields = {field.name for field in ShoppingClickEvent._meta.fields}
    assert "ip_address" not in fields
    assert "user_agent" not in fields


@pytest.mark.django_db
@override_settings(LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS=5)
def test_shopping_click_dedupe_does_not_block_redirect():
    post = make_post()
    product = make_product(post)
    client = Client(REMOTE_ADDR="203.0.113.77")

    first = client.get(f"/go/shop/{post.slug}/{product.slug}/")
    second = client.get(f"/go/shop/{post.slug}/{product.slug}/")

    assert first.status_code == second.status_code == 302
    assert ShoppingClickEvent.objects.count() == 1


@pytest.mark.django_db
def test_inactive_or_expired_product_is_not_publicly_clickable():
    post = make_post()
    inactive = make_product(post, slug="inactive", active=False)
    expired = ShoppingProduct.objects.create(
        post=post,
        position=2,
        name="Expired Item",
        slug="expired",
        affiliate_url="https://shopee.ph/expired",
        expires_at=timezone.now() - timedelta(minutes=1),
    )

    client = Client()
    assert client.get(f"/go/shop/{post.slug}/{inactive.slug}/").status_code == 404
    assert client.get(f"/go/shop/{post.slug}/{expired.slug}/").status_code == 404
    detail = client.get(f"/api/public/shop/{post.slug}/").json()
    assert detail["products"] == []


@pytest.mark.django_db
def test_shopping_affiliate_url_requires_https():
    post = make_post()
    product = ShoppingProduct(
        post=post,
        position=1,
        name="Unsafe item",
        slug="unsafe-item",
        affiliate_url="http://example.test/not-secure",
    )
    with pytest.raises(ValidationError):
        product.full_clean()


@pytest.mark.django_db
def test_shopping_image_fields_are_manual_cms_uploads(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    post = make_post(status=ShoppingPost.Status.DRAFT)
    post.cover_image = SimpleUploadedFile("cover.jpg", b"manual-cover", content_type="image/jpeg")
    post.full_clean()
    post.save()
    assert post.cover_image.name.endswith("cover.jpg")


@pytest.mark.django_db
@override_settings(LEARNLOOT_PUBLIC_BASE_URL="https://learnloot.test")
def test_course_cms_overrides_public_content_and_seo_without_changing_scraped_source(provider):
    course = make_public_course(provider)
    course.editorial_title = "Editor-picked Python Course"
    course.editorial_description = "Original LearnLoot editorial summary."
    course.seo_title = "Free Python Course - LearnLoot Editor Pick"
    course.meta_description = "A curated description for search and social previews."
    course.meta_keywords = "free python course, python udemy"
    course.save()

    payload = Client().get(f"/api/public/courses/{provider.slug}/{course.slug}/").json()

    assert course.title == "Scraped Python Course"
    assert course.description == "Scraped provider description."
    assert payload["title"] == course.editorial_title
    assert payload["description"] == course.editorial_description
    assert payload["seo"]["title"] == course.seo_title
    assert payload["seo"]["description"] == course.meta_description
    assert payload["seo"]["keywords"] == course.meta_keywords


@pytest.mark.django_db
def test_discovery_refreshes_scraped_fields_but_preserves_course_cms_overrides(provider):
    first = NormalizedCourse(
        external_id="cms-course",
        title="Original scraped title",
        canonical_url="https://www.udemy.com/course/cms-course/",
        source_url="https://www.udemy.com/courses/free/",
        source_type="listing",
        thumbnail_url="https://example.test/one.jpg",
        instructor_name="Instructor",
        rating=Decimal("4.50"),
        review_count=500,
        student_count=1000,
        duration_minutes=120,
        description="Original scraped description",
        price_amount=Decimal("0.00"),
        currency="USD",
        is_free=True,
        price_type="free",
    )
    result = upsert_course(provider, first)
    course = result.course
    course.editorial_title = "CMS title"
    course.editorial_description = "CMS description"
    course.meta_description = "CMS SEO description"
    course.save()

    second = NormalizedCourse(
        external_id="cms-course",
        title="Refreshed scraped title",
        canonical_url="https://www.udemy.com/course/cms-course/",
        source_url="https://www.udemy.com/courses/free/",
        source_type="listing",
        thumbnail_url="https://example.test/two.jpg",
        instructor_name="Instructor Two",
        rating=Decimal("4.70"),
        review_count=700,
        student_count=1500,
        duration_minutes=140,
        description="Refreshed scraped description",
        price_amount=Decimal("0.00"),
        currency="USD",
        is_free=True,
        price_type="free",
    )
    upsert_course(provider, second)
    course.refresh_from_db()

    assert course.title == "Refreshed scraped title"
    assert course.description == "Refreshed scraped description"
    assert course.editorial_title == "CMS title"
    assert course.editorial_description == "CMS description"
    assert course.meta_description == "CMS SEO description"
    assert course.public_title == "CMS title"


@pytest.mark.django_db
@override_settings(LEARNLOOT_PUBLIC_BASE_URL="https://learnloot.test")
def test_public_sitemap_feeds_include_only_indexable_course_and_shopping_pages(provider):
    course = make_public_course(provider)
    published = make_post()
    make_product(published)
    draft = ShoppingPost.objects.create(
        title="Draft post",
        slug="draft-post",
        status=ShoppingPost.Status.DRAFT,
    )

    course_urls = {item["url"] for item in Client().get("/api/public/courses/sitemap/").json()["results"]}
    shopping_urls = {item["url"] for item in Client().get("/api/public/shop/sitemap/").json()["results"]}

    assert f"https://learnloot.test/courses/udemy/{course.slug}" in course_urls
    assert f"https://learnloot.test/shop/{published.slug}" in shopping_urls
    assert f"https://learnloot.test/shop/{draft.slug}" not in shopping_urls


def test_phase9b_admin_and_frontend_seo_foundation_are_present():
    root = Path(__file__).resolve().parents[2]
    course_admin = admin.site._registry[Course]
    shopping_admin = admin.site._registry[ShoppingPost]

    assert isinstance(course_admin, CourseAdmin)
    assert "editorial_title" in str(course_admin.fieldsets)
    assert "meta_description" in str(course_admin.fieldsets)
    assert isinstance(shopping_admin, ShoppingPostAdmin)

    layout = (root / "frontend" / "src" / "app" / "layout.tsx").read_text(encoding="utf-8")
    course_page = (root / "frontend" / "src" / "app" / "courses" / "[provider]" / "[slug]" / "page.tsx").read_text(encoding="utf-8")
    shop_page = (root / "frontend" / "src" / "app" / "shop" / "[slug]" / "page.tsx").read_text(encoding="utf-8")
    robots = (root / "frontend" / "src" / "app" / "robots.ts").read_text(encoding="utf-8")
    sitemap = (root / "frontend" / "src" / "app" / "sitemap.ts").read_text(encoding="utf-8")

    assert "GOOGLE_SITE_VERIFICATION" in layout
    assert "keywords:" in layout
    assert "openGraph" in layout
    assert "twitter" in layout
    assert "course.seo" in course_page
    assert 'rel="sponsored nofollow noopener noreferrer"' in shop_page
    assert "Article" in shop_page and "ItemList" in shop_page and "BreadcrumbList" in shop_page
    assert "MetadataRoute.Robots" in robots
    assert "MetadataRoute.Sitemap" in sitemap
    assert (root / "frontend" / "src" / "app" / "shop" / "top-10" / "page.tsx").exists()
    assert (root / "frontend" / "src" / "app" / "shop" / "flash-deals" / "page.tsx").exists()
