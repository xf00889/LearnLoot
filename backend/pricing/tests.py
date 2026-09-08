from decimal import Decimal

import pytest

from courses.models import Course
from pricing.models import CoursePrice
from providers.models import Provider


@pytest.mark.django_db
def test_course_price_preserves_multiple_historical_observations():
    provider = Provider.objects.create(name="Udemy", slug="udemy")
    course = Course.objects.create(
        provider=provider,
        external_id="course-123",
        title="Python Course",
        slug="python-course",
        canonical_url="https://example.com/courses/course-123",
    )

    CoursePrice.objects.create(
        course=course,
        amount=Decimal("19.99"),
        currency="USD",
        is_free=False,
        price_type="sale",
    )
    CoursePrice.objects.create(
        course=course,
        amount=Decimal("0.00"),
        currency="USD",
        is_free=True,
        price_type="free",
    )

    prices = list(course.prices.order_by("observed_at", "id"))

    assert len(prices) == 2
    assert prices[0].amount == Decimal("19.99")
    assert prices[0].is_free is False
    assert prices[1].amount == Decimal("0.00")
    assert prices[1].is_free is True