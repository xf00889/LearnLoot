import os
import tempfile


BOT_NAME = "learnloot"

SPIDER_MODULES = ["discovery.scrapy_app.spiders"]
NEWSPIDER_MODULE = "discovery.scrapy_app.spiders"

# Compliance and load controls. This crawler must not be configured to bypass
# access controls, CAPTCHA challenges, or a provider's explicit blocks.
ROBOTSTXT_OBEY = True
ROBOTSTXT_USER_AGENT = "LearnLootBot"

USER_AGENT = os.environ.get("LEARNLOOT_CRAWLER_USER_AGENT", "LearnLootBot/0.1")
DEFAULT_REQUEST_HEADERS = {
    "Accept-Language": "en-US,en;q=0.8",
}

CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 3.0
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 30

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3.0
AUTOTHROTTLE_MAX_DELAY = 60.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5
AUTOTHROTTLE_DEBUG = False

RETRY_ENABLED = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504]

HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_POLICY = "scrapy.extensions.httpcache.RFC2616Policy"
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"
HTTPCACHE_DIR = os.path.join(tempfile.gettempdir(), "learnloot-scrapy-httpcache")

TELNETCONSOLE_ENABLED = False
COOKIES_ENABLED = False

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

DOWNLOAD_HANDLERS = {
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
}
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "user_agent": USER_AGENT,
    }
}
PLAYWRIGHT_MAX_CONTEXTS = 1
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 1
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000
PLAYWRIGHT_ABORT_REQUEST = "discovery.scrapy_app.settings.should_abort_request"

LOG_LEVEL = os.environ.get("LEARNLOOT_SCRAPY_LOG_LEVEL", "INFO")


def should_abort_request(request) -> bool:
    """Skip heavy assets that are not required to read public course metadata."""

    return request.resource_type in {"image", "media", "font"}