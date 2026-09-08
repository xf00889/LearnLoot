import json
import subprocess
from pathlib import Path

from scrapy.http import HtmlResponse, Request

from discovery.scrapy_app import settings
from discovery.scrapy_app.extractors import extract_udemy_free_records
from discovery.scrapy_app.runner import ScrapyUdemySource
from discovery.scrapy_app.spiders.udemy_free import UdemyFreeSpider


RENDERED_FIXTURE = """
<html>
  <body>
    <article class="course-card" data-course-id="12345">
      <a href="/course/python-for-beginners/?utm_source=test" aria-label="Python for Beginners">
        Open course
      </a>
      <div data-purpose="instructor-name">Ada Example</div>
      <span aria-label="4.7 rating">4.7</span>
      <span>1,234 ratings</span>
      <img src="https://img-c.udemycdn.com/course/480x270/python.jpg">
    </article>
    <li class="course-card">
      <h3><a href="/course/javascript-basics/">JavaScript Basics</a></h3>
      <div class="instructor-name">Grace Example</div>
      <span aria-label="4.5 rating">4.5</span>
      <span>99 reviews</span>
    </li>
    <a href="/course/python-for-beginners/">duplicate</a>
  </body>
</html>
"""



LIVE_STYLE_RENDERED_FIXTURE = """
<html>
  <body>
    <article class="course-card">
      <a
        href="/course/manageyourtime/"
        aria-label="A Mini Course on Time Management 7 steps you can use immediately to become more productive and master time management Rating: 4.4 out of 5 55847 reviews 0.5 total hours 12 lectures All Levels"
      >
        <span data-purpose="course-title-url">A Mini Course on Time Management</span>
        <span>
          7 steps you can use immediately to become more productive and master time management
        </span>
        <span aria-label="Rating: 4.4 out of 5">4.4</span>
        <span>55847 reviews</span>
        <span>0.5 total hours</span>
        <span>12 lectures</span>
        <span>All Levels</span>
      </a>
    </article>
  </body>
</html>
"""


def live_style_rendered_response():
    url = "https://www.udemy.com/courses/free/?p=1"
    return HtmlResponse(
        url=url,
        request=Request(url=url),
        body=LIVE_STYLE_RENDERED_FIXTURE.encode(),
        encoding="utf-8",
    )



ACTUAL_2026_UDEMY_CARD_FIXTURE = """
<html>
  <body>
    <article class="course-card">
      <h3
        data-purpose="course-title-url"
        class="ud-heading-md course-card-title_course-title___sH9w"
      >
        <a href="/course/manageyourtime/" target="_blank" rel="noopener">A Mini Course on Time Management<div class="ud-sr-only" aria-hidden="true"><span data-testid="seo-headline">7 steps you can use immediately to become more productive and master time management</span><span data-testid="seo-rating">Rating: 4.4 out of 5</span><span data-testid="seo-num-reviews">55847 reviews</span><span data-testid="seo-content-info">0.5 total hours</span><span data-testid="seo-num-lectures">12 lectures</span><span data-testid="seo-instructional-level">All Levels</span></div></a>
      </h3>
    </article>
  </body>
</html>
"""


def actual_2026_udemy_card_response():
    url = "https://www.udemy.com/courses/free/?p=1"
    return HtmlResponse(
        url=url,
        request=Request(url=url),
        body=ACTUAL_2026_UDEMY_CARD_FIXTURE.encode(),
        encoding="utf-8",
    )


def rendered_response(url="https://www.udemy.com/courses/free/?p=1"):
    request = Request(url=url)
    return HtmlResponse(
        url=url,
        request=request,
        body=RENDERED_FIXTURE.encode(),
        encoding="utf-8",
    )


def test_scrapy_settings_are_polite_and_robots_compliant():
    assert settings.ROBOTSTXT_OBEY is True
    assert settings.CONCURRENT_REQUESTS == 1
    assert settings.CONCURRENT_REQUESTS_PER_DOMAIN == 1
    assert settings.DOWNLOAD_DELAY >= 3
    assert settings.AUTOTHROTTLE_ENABLED is True
    assert settings.AUTOTHROTTLE_TARGET_CONCURRENCY == 0.5
    assert settings.RETRY_ENABLED is True
    assert 429 in settings.RETRY_HTTP_CODES
    assert settings.HTTPCACHE_ENABLED is True
    assert settings.PLAYWRIGHT_MAX_CONTEXTS == 1
    assert settings.PLAYWRIGHT_MAX_PAGES_PER_CONTEXT == 1


def test_scrapy_settings_do_not_configure_stealth_or_proxy_bypass():
    assert "PLAYWRIGHT_BROWSER_PROVIDER" not in settings.__dict__
    assert "PLAYWRIGHT_CDP_URL" not in settings.__dict__
    assert "PLAYWRIGHT_CONNECT_URL" not in settings.__dict__
    assert "HTTPPROXY_ENABLED" not in settings.__dict__


def test_rendered_course_extractor_finds_and_deduplicates_cards():
    records = extract_udemy_free_records(rendered_response())

    assert len(records) == 2

    first = records[0]
    assert first["id"] == "12345"
    assert first["identity_kind"] == "numeric"
    assert first["title"] == "Python for Beginners"
    assert first["url"] == "https://www.udemy.com/course/python-for-beginners/"
    assert first["visible_instructors"] == [{"display_name": "Ada Example"}]
    assert first["avg_rating"] == "4.7"
    assert first["num_reviews"] == 1234
    assert first["is_paid"] is False
    assert first["catalog_kind"] == "free"

    second = records[1]
    assert second["id"] == "slug:javascript-basics"
    assert second["identity_kind"] == "slug"


def test_live_style_course_title_excludes_card_summary_metadata():
    records = extract_udemy_free_records(live_style_rendered_response())

    assert len(records) == 1
    record = records[0]
    assert record["title"] == "A Mini Course on Time Management"
    assert "Rating:" not in record["title"]
    assert "55847 reviews" not in record["title"]
    assert "lectures" not in record["title"]
    assert record["avg_rating"] == "4.4"
    assert record["num_reviews"] == 55847


def test_summary_like_anchor_label_falls_back_to_clean_slug_title():
    html = """
    <html>
      <body>
        <article class="course-card">
          <a
            href="/course/code-your-first-game/"
            aria-label="Code Your First Game Learn JavaScript Rating: 4.4 out of 5 29150 reviews 2 total hours 12 lectures Beginner"
          >
            Code Your First Game Learn JavaScript Rating: 4.4 out of 5
            29150 reviews 2 total hours 12 lectures Beginner
          </a>
        </article>
      </body>
    </html>
    """
    url = "https://www.udemy.com/courses/free/?p=1"
    response = HtmlResponse(
        url=url,
        request=Request(url=url),
        body=html.encode(),
        encoding="utf-8",
    )

    records = extract_udemy_free_records(response)

    assert len(records) == 1
    assert records[0]["title"] == "Code Your First Game"
    assert "Rating:" not in records[0]["title"]


def test_legitimate_short_title_with_beginner_word_is_not_rejected():
    html = """
    <html>
      <body>
        <article class="course-card">
          <a href="/course/beginner-python/" aria-label="Beginner Python">
            Beginner Python
          </a>
        </article>
      </body>
    </html>
    """
    url = "https://www.udemy.com/courses/free/?p=1"
    response = HtmlResponse(
        url=url,
        request=Request(url=url),
        body=html.encode(),
        encoding="utf-8",
    )

    records = extract_udemy_free_records(response)

    assert len(records) == 1
    assert records[0]["title"] == "Beginner Python"


def test_exact_dom_fix_preserves_semantic_title_child_compatibility():
    records = extract_udemy_free_records(live_style_rendered_response())

    assert len(records) == 1
    record = records[0]
    assert record["title"] == "A Mini Course on Time Management"
    assert record["avg_rating"] == "4.4"
    assert record["num_reviews"] == 55847
    assert "Rating:" not in record["title"]
    assert "reviews" not in record["title"]


def test_actual_2026_udemy_dom_extracts_exact_public_metadata():
    records = extract_udemy_free_records(actual_2026_udemy_card_response())

    assert len(records) == 1
    record = records[0]

    assert record["id"] == "slug:manageyourtime"
    assert record["identity_kind"] == "slug"
    assert record["title"] == "A Mini Course on Time Management"
    assert record["avg_rating"] == "4.4"
    assert record["num_reviews"] == 55847
    assert (
        record["headline"]
        == "7 steps you can use immediately to become more productive and master time management"
    )
    assert record["url"] == "https://www.udemy.com/course/manageyourtime/"
    assert "Rating:" not in record["title"]
    assert "reviews" not in record["title"]
    assert "lectures" not in record["title"]


def test_spider_builds_bounded_playwright_request():
    spider = UdemyFreeSpider(max_pages="2", item_limit="5", render_wait_ms="2500")

    request = spider._page_request(1)

    assert request.url == "https://www.udemy.com/courses/free/?p=1"
    assert request.meta["playwright"] is True
    assert request.meta["learnloot_page_number"] == 1
    assert len(request.meta["playwright_page_methods"]) == 1


def test_spider_paginates_only_after_finding_course_cards():
    spider = UdemyFreeSpider(max_pages="2", render_wait_ms="0")

    outputs = list(spider.parse(rendered_response()))

    records = [item for item in outputs if isinstance(item, dict)]
    requests = [item for item in outputs if isinstance(item, Request)]

    assert len(records) == 2
    assert len(requests) == 1
    assert requests[0].url == "https://www.udemy.com/courses/free/?p=2"


def test_scrapy_runner_uses_isolated_subprocess_and_reads_jsonl(tmp_path):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        output_path = Path(command[command.index("-O") + 1])
        output_path.write_text(
            json.dumps({"id": "slug:python", "catalog_kind": "free"}) + "\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    runner = ScrapyUdemySource(
        python_executable="python-test",
        backend_dir=tmp_path,
        run=fake_run,
    )

    records = list(
        runner.crawl(
            "https://www.udemy.com/courses/free/",
            max_pages=1,
            item_limit=5,
            render_wait_ms=2500,
        )
    )

    assert records == [{"id": "slug:python", "catalog_kind": "free"}]
    assert captured["command"][:5] == [
        "python-test",
        "-m",
        "scrapy",
        "crawl",
        "udemy_free",
    ]
    assert captured["kwargs"]["cwd"] == str(tmp_path)
    assert (
        captured["kwargs"]["env"]["SCRAPY_SETTINGS_MODULE"]
        == "discovery.scrapy_app.settings"
    )