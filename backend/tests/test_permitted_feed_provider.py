import io
from email.message import Message
from urllib.error import HTTPError, URLError
from unittest.mock import patch

import pytest

from courses.models import Course
from discovery.http import HttpClientError, HttpResponseError, JsonHttpClient
from discovery.models import DiscoveryRun
from discovery.providers.approved_json_feed import (
    ApprovedFeedConfig,
    ApprovedJsonFeedProvider,
)
from discovery.services import DiscoveryExecutionError, execute_discovery
from pricing.models import CoursePrice
from providers.models import Provider


class StubJsonClient:
    def __init__(self, responses):
        self.responses = dict(responses)
        self.calls = []

    def get_json(self, url, headers=None):
        self.calls.append((url, dict(headers or {})))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response


def feed_record(
    external_id="approved-101",
    *,
    title="Approved Python Course",
    amount="0.00",
    is_free=True,
):
    return {
        "id": external_id,
        "title": title,
        "url": f"https://provider.example/courses/{external_id}",
        "thumbnail_url": f"https://provider.example/images/{external_id}.jpg",
        "instructor_name": "Approved Instructor",
        "rating": "4.80",
        "review_count": 140,
        "student_count": 3200,
        "duration_minutes": 210,
        "description": "Approved partner feed test record.",
        "offer": {
            "amount": amount,
            "currency": "USD",
            "is_free": is_free,
            "type": "promotion",
        },
    }


@pytest.fixture
def provider():
    return Provider.objects.create(name="Approved Feed", slug="approved-feed")


@pytest.mark.django_db
def test_approved_feed_runs_paginated_discovery_pipeline(provider):
    first_url = "https://feed.example.test/courses?page=1"
    second_url = "https://feed.example.test/courses?page=2"
    client = StubJsonClient(
        {
            first_url: {
                "results": [feed_record("approved-101")],
                "next": "/courses?page=2",
            },
            second_url: {
                "results": [feed_record("approved-202")],
                "next": None,
            },
        }
    )
    connector = ApprovedJsonFeedProvider(
        ApprovedFeedConfig(
            provider_key="approved-feed",
            access_approved=True,
            headers={"Authorization": "Bearer test-secret"},
        ),
        client=client,
    )

    run = execute_discovery(provider, connector, first_url)

    assert run.status == DiscoveryRun.Status.SUCCEEDED
    assert run.records_found == 2
    assert run.records_new == 2
    assert Course.objects.filter(provider=provider).count() == 2
    assert CoursePrice.objects.count() == 2
    assert [call[0] for call in client.calls] == [first_url, second_url]


@pytest.mark.django_db
def test_feed_access_must_be_explicitly_approved(provider):
    connector = ApprovedJsonFeedProvider(
        ApprovedFeedConfig(provider_key="approved-feed", access_approved=False),
        client=StubJsonClient({}),
    )

    with pytest.raises(DiscoveryExecutionError) as exc_info:
        execute_discovery(provider, connector, "https://feed.example.test/courses")

    run = DiscoveryRun.objects.get(pk=exc_info.value.run_id)
    assert run.status == DiscoveryRun.Status.FAILED
    assert Course.objects.count() == 0


@pytest.mark.django_db
def test_cross_origin_pagination_is_rejected(provider):
    source = "https://feed.example.test/courses"
    connector = ApprovedJsonFeedProvider(
        ApprovedFeedConfig(provider_key="approved-feed", access_approved=True),
        client=StubJsonClient(
            {
                source: {
                    "results": [feed_record()],
                    "next": "https://unapproved.example.test/courses?page=2",
                }
            }
        ),
    )

    with pytest.raises(DiscoveryExecutionError):
        execute_discovery(provider, connector, source)

    assert Course.objects.filter(provider=provider, external_id="approved-101").exists()
    assert Course.objects.filter(provider=provider).count() == 1


@pytest.mark.django_db
def test_feed_rejects_http_source_without_network_access(provider):
    connector = ApprovedJsonFeedProvider(
        ApprovedFeedConfig(provider_key="approved-feed", access_approved=True),
        client=StubJsonClient({}),
    )

    with pytest.raises(DiscoveryExecutionError):
        execute_discovery(provider, connector, "http://feed.example.test/courses")

    assert Course.objects.count() == 0


@pytest.mark.django_db
def test_malformed_results_fail_run_without_removing_existing_course(provider):
    source = "https://feed.example.test/courses"
    existing = Course.objects.create(
        provider=provider,
        external_id="existing-1",
        title="Existing Course",
        slug="existing-course",
        canonical_url="https://provider.example/courses/existing-1",
    )
    connector = ApprovedJsonFeedProvider(
        ApprovedFeedConfig(provider_key="approved-feed", access_approved=True),
        client=StubJsonClient({source: {"results": "not-a-list", "next": None}}),
    )

    with pytest.raises(DiscoveryExecutionError):
        execute_discovery(provider, connector, source)

    existing.refresh_from_db()
    assert existing.status == Course.Status.ACTIVE
    assert Course.objects.filter(pk=existing.pk).exists()


def _headers(content_type="application/json; charset=utf-8"):
    headers = Message()
    headers["Content-Type"] = content_type
    return headers


class FakeUrlResponse:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.headers = _headers()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, limit):
        return self.payload[:limit]


def test_http_client_retries_retryable_status_and_honors_retry_after():
    sleeps = []
    client = JsonHttpClient(max_retries=1, sleep=sleeps.append)
    retry_headers = Message()
    retry_headers["Retry-After"] = "2"
    retry_error = HTTPError(
        "https://feed.example.test/courses",
        429,
        "rate limited",
        retry_headers,
        io.BytesIO(b""),
    )

    with patch(
        "discovery.http.urlopen",
        side_effect=[retry_error, FakeUrlResponse(b'{"results": [], "next": null}')],
    ):
        result = client.get_json("https://feed.example.test/courses")

    assert result["results"] == []
    assert sleeps == [2.0]


def test_http_client_retries_transient_network_failure():
    sleeps = []
    client = JsonHttpClient(max_retries=1, backoff_seconds=0.5, sleep=sleeps.append)

    with patch(
        "discovery.http.urlopen",
        side_effect=[URLError("temporary"), FakeUrlResponse(b'{"results": []}')],
    ):
        result = client.get_json("https://feed.example.test/courses")

    assert result == {"results": []}
    assert sleeps == [0.5]


def test_http_client_does_not_retry_non_retryable_404():
    client = JsonHttpClient(max_retries=3, sleep=lambda _delay: None)
    not_found = HTTPError(
        "https://feed.example.test/courses",
        404,
        "not found",
        Message(),
        io.BytesIO(b""),
    )

    with patch("discovery.http.urlopen", side_effect=not_found) as mocked_urlopen:
        with pytest.raises(HttpClientError, match="HTTP 404"):
            client.get_json("https://feed.example.test/courses")

    assert mocked_urlopen.call_count == 1


def test_http_client_rejects_malformed_json():
    client = JsonHttpClient(max_retries=0)

    with patch("discovery.http.urlopen", return_value=FakeUrlResponse(b"not-json")):
        with pytest.raises(HttpResponseError, match="not valid JSON"):
            client.get_json("https://feed.example.test/courses")