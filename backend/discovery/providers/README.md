# Provider connectors

Provider connectors must use a data-access method that is explicitly permitted for automated use.

`ApprovedJsonFeedProvider` is for an HTTPS JSON feed/API that the operator is authorized to consume. Setting `access_approved=True` is an operational assertion, not a permission grant from LearnLoot.

Do not point this connector at ordinary provider website pages. It expects provider-controlled JSON and preserves provider-specific parsing inside the discovery layer.

## Udemy free-course connector

LearnLoot uses this fixed Udemy SQL, Free, and English course search:

`https://www.udemy.com/courses/search/?q=sql+course&src=sac&price=price-free&lang=en`

The admin supplies only the requested course count. The source normalizer routes
every discovery run through this URL. Repeated listings are skipped before
persistence, and the database pipeline updates an existing course instead of
creating a duplicate. If Udemy's current robots directives disallow that URL or
an access challenge is returned, the run fails visibly; the crawler does not
bypass either restriction.

The crawler is intentionally configured for compliance and low load:

- `ROBOTSTXT_OBEY = True`
- one concurrent request per domain
- a non-zero download delay
- Scrapy AutoThrottle
- bounded retries for temporary failures such as 429/5xx
- HTTP caching
- bounded pagination
- one Playwright browser context/page at a time
- heavy image/media/font downloads are skipped
- no login automation
- no CAPTCHA bypass
- no fingerprint/stealth plugins
- no proxy rotation intended to bypass provider blocks
- no access-control bypass
- no paid lesson/media scraping
- no learner/private-data collection

Playwright is used only to render the public SQL course-search page because the initial HTML shell does not contain the course cards.

The spider accepts genuine free-catalog records only. When the rendered public card exposes a numeric course id it is used. When it does not, LearnLoot temporarily uses a namespaced `slug:<course-slug>` identity until a permitted source exposes the canonical numeric provider id.

`access_approved=True` remains an operator acknowledgement, not a permission grant. Review Udemy's current Terms, robots/access policy, and other applicable requirements before live crawling.

Read-only live verification:

```powershell
python backend\manage.py smoke_udemy_free --acknowledge-access-terms --limit 5
```

The smoke command validates rendered records and does not persist courses.
