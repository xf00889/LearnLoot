# LearnLoot Course Deals Platform

## Stack

- Django + Django REST Framework
- PostgreSQL
- Redis + Celery
- Scrapy + scrapy-playwright
- Next.js + React + TypeScript + Tailwind CSS

## Local infrastructure

For the primary Windows development setup, use EnvKit PostgreSQL 17.x on
`127.0.0.1:5432` and EnvKit Redis on `127.0.0.1:6379`. Docker Compose remains
available in `infrastructure/docker-compose.yml` as an optional alternative,
but it is not required for local LearnLoot development.

Copy `.env.example` to `.env` and provide local values. Automated Udemy
discovery remains disabled by default. Set
`LEARNLOOT_UDEMY_DISCOVERY_ACCESS_APPROVED=true` only after reviewing the
provider's current terms, robots directives, and permitted automated-access
method for the configured public source.

## Backend

```bash
python backend/manage.py check
python backend/manage.py migrate
python -m pytest backend
```

## Celery discovery worker

The Django admin queues discovery; it does not run Scrapy or Playwright inside
the HTTP request. Start a worker from the project root after Redis is available.
On Windows, use Celery's solo pool for local development:

```bash
celery -A config --workdir backend worker --loglevel=INFO --pool=solo
```

On platforms where Celery's normal worker pool is supported, omit
`--pool=solo` unless your deployment requires it.

In local `DEBUG` mode, the custom admin discovery action can start this same
worker automatically when none responds. The command and arguments are fixed
in code and no HTTP input is executed. Set
`LEARNLOOT_ADMIN_AUTO_START_CELERY_WORKER=false` to require manual startup.
Production continues to require a separately supervised worker.

## Admin discovery operations

1. Create or verify the `Udemy` provider with slug `udemy`.
2. Keep the provider Active.
3. Confirm the Provider admin reports discovery as `Ready`.
4. Select the provider and choose **Queue discovery for selected providers**.
5. Inspect Discovery Runs, observations, courses, sources, and price history in
   Django admin.

The custom admin accepts the number of courses to collect and uses the fixed
Udemy SQL, Free, and English search URL. Duplicate listings are skipped during
the crawl and existing courses are updated instead of inserted again. A robots
denial or access challenge is reported as a failed run rather than a successful
run with zero records.

Discovery runs and observation/price/source history are treated as audit data
and are read-only in the admin. Course visibility is controlled with Activate,
Hide, and Archive admin actions.

## Phase 6 publication eligibility

Discovery now feeds a deterministic publication-eligibility stage. A course is
never queued unless its provider and course are active, the latest known price
state is genuinely free, and the course was checked recently. Quality rules use
rating, review count, a deterministic 0-100 score, and a publication cooldown.
Admin force-eligible overrides may bypass quality/cooldown rules, but they do
not bypass inactive/hidden/archive, non-free, conflicting-free-price, or stale
course safety gates. Force-ineligible overrides always block publication.

Eligible courses are placed in `publication_queue`. Phase 6 does not send
Telegram messages; delivery and retry behavior are reserved for Phase 7.
Django admin exposes current eligibility, override state, queue history, and
manual queue/evaluation actions.

## Phase 7 Telegram channel publication

LearnLoot publishes selected course deals to a **Telegram channel** so followers
receive new-deal alerts and the posts drive traffic back to LearnLoot. The
channel is the audience/distribution destination. A Telegram bot is still used
as the official automation credential/API client; it is not the destination.

Setup:

1. Create or choose the Telegram channel you want people to follow.
2. Create a Telegram bot for automation and keep its token secret.
3. Add that bot as an administrator of the channel with permission to post
   messages.
4. Set `LEARNLOOT_TELEGRAM_CHANNEL_ID` to the public channel username such as
   `@your_channel`, or to the numeric channel id when appropriate.
5. Set `LEARNLOOT_PUBLIC_BASE_URL` to the public LearnLoot website URL.
6. Keep `LEARNLOOT_TELEGRAM_ENABLED=false` until the channel setup is verified,
   then enable it when you are ready for automated posts.

Phase 7 consumes `publication_queue` through Celery and records Telegram channel
delivery state, attempt counts, timestamps, and the returned message id in
`telegram_posts`.

Posts link to the LearnLoot landing route
`/courses/<provider-slug>/<course-slug>` rather than linking directly to Udemy.
This keeps Telegram as a traffic-acquisition channel while the website remains
the owned SEO/analytics asset. Phase 8 implements the public frontend route and
its social/Open Graph presentation.

Delivery performs a fresh Phase 6 eligibility check immediately before sending.
If a course became paid, hidden, archived, stale, or otherwise ineligible, its
queue item is cancelled without contacting Telegram.

Successful sends are application-idempotent: once Telegram returns a message id,
the queue item and `telegram_posts` record are committed as sent and repeated
tasks do not resend. Telegram's `sendMessage` method does not expose an
application idempotency key, so network failures can have an ambiguous outcome.
LearnLoot does not automatically retry those failures; it records them as
Ambiguous so an operator can verify the channel first. Explicit flood-control
responses (`retry_after`) use bounded Celery retry/backoff.

No bot token or raw channel destination is stored in the database. Delivery
records store only a keyed SHA-256 target fingerprint, rendered message snapshot,
LearnLoot landing URL, message id, attempts, timestamps, and sanitized errors.

At the Telegram Bot API transport layer the destination field is still named
`chat_id`; Telegram uses that same API parameter for channels. LearnLoot exposes
the application setting as `LEARNLOOT_TELEGRAM_CHANNEL_ID` so the product
configuration reflects the actual destination.

## Phase 8 public website

Phase 8 adds the public LearnLoot website route used by Telegram channel posts.
The backend exposes read-only public JSON under `/api/public/courses/`. Public
results are restricted to active providers, active courses, recent successful
course checks, current free price state, and an eligibility decision that is at
least as recent as the latest course check.

The Next.js frontend implements:

- `/` for the latest qualified free courses and Telegram follower CTA.
- `/courses` for a searchable public catalog.
- `/courses/<provider-slug>/<course-slug>` for the SEO landing page linked from
  Telegram channel posts.

Frontend runtime configuration belongs in `frontend/.env.local`; copy it from
`frontend/.env.example`. Set `NEXT_PUBLIC_API_BASE_URL` to the Django API,
`NEXT_PUBLIC_SITE_URL` to the public LearnLoot site, and
`NEXT_PUBLIC_TELEGRAM_CHANNEL_URL` to the public Telegram channel URL.

Keep backend `LEARNLOOT_PUBLIC_BASE_URL` aligned with `NEXT_PUBLIC_SITE_URL`
before enabling real Telegram channel publication. Course detail pages display
the latest check time and a changing-availability disclaimer before visitors
continue to the provider.

## Phase 9 course outbound tracking

Phase 9 routes course CTAs through the controlled backend endpoint
`/go/<provider-slug>/<course-slug>/`. The redirect reuses Phase 8 public-course
safety checks immediately before leaving LearnLoot, validates the course's
canonical HTTPS provider URL, records a privacy-minimized click event, and then
redirects the visitor to that provider page.

Course-provider affiliate support has been removed. LearnLoot does not apply an
affiliate destination to Udemy course links, and the public course API exposes
only the controlled `outbound_url`, not raw provider URLs or affiliate flags.

`click_events` stores only the course, source, campaign, and timestamp. IP
addresses and user-agent strings are not persisted. A short configurable
cache-only dedupe window reduces accidental double-click inflation while still
allowing every request to redirect. Set
`LEARNLOOT_OUTBOUND_CLICK_DEDUPE_SECONDS` to tune or disable that window.

Telegram posts include `source=telegram&campaign=channel` on their LearnLoot
landing URL. The course page carries those attribution values forward to
`/go/...`; direct catalog visits default to `source=course_page`.

## Phase 9B shopping editorial CMS and site-wide SEO

Phase 9B adds a dedicated `shopping` domain for manually curated Shopee affiliate
content. This remains separate from Udemy/course links. Course outbound links are
still non-affiliate and always resolve to the validated canonical provider URL.

Django Admin now supports shopping posts with types such as Top 10 lists, flash
deals, buying guides, roundups, and articles. Each post has a manual slug, excerpt,
body, cover image, publication state, SEO title, meta description, meta keywords,
and optional featured flag. Products are managed inline with rank/position, image,
original editorial description, optional display prices, badge, pros/cons,
expiration, and a private HTTPS affiliate destination. Public APIs expose only the
controlled `/go/shop/...` URL, never the raw affiliate URL.

Shopping click analytics are stored separately in `shopping_click_events`. They
retain only product, source, campaign, and timestamp; IP addresses and user-agent
strings are not persisted. A short HMAC/cache-only dedupe window reduces accidental
double clicks. Redirect responses are no-store and noindex.

Scraped courses are also CMS-editable without losing source integrity. Discovery
continues to refresh scraped fields while operator-controlled editorial title,
description, image, slug, SEO title, meta description, meta keywords, and social
image remain persistent. Blank CMS overrides fall back to the latest scraped value.

The public frontend adds `/shop`, `/shop/top-10`, `/shop/flash-deals`,
`/shop/guides`, and `/shop/<slug>`. Site-wide metadata uses the Next.js Metadata
API for titles, descriptions, author/publisher, meta keywords, canonical URLs,
Open Graph, Twitter cards, crawler directives, and optional Google site
verification. Next.js also serves `/robots.txt` and `/sitemap.xml`. Course pages
emit Course + BreadcrumbList JSON-LD; shopping articles emit Article + ItemList +
BreadcrumbList JSON-LD. Affiliate CTAs are marked `rel="sponsored nofollow"` and
shopping pages display an affiliate disclosure.

Uploaded CMS media is stored under `backend/media/` in local development and is
served by Django only when `DEBUG` is enabled. Production deployment should use a
persistent media volume/object store and a web server/CDN rather than Django's
development media serving.

## Phase 10 production readiness and operations

Phase 10 adds fail-closed production configuration checks, liveness/readiness
health endpoints, shared Redis-cache support, production security settings,
stdout logging, scheduled Celery automation, operational status output, and
PostgreSQL backup/verification commands. It does not change the Phase 9B public
SEO/CMS routes or add a database migration.

Local Windows development remains EnvKit-first. Production automation is
explicitly disabled until `LEARNLOOT_AUTOMATION_ENABLED=true`, and only one
Celery beat scheduler should run for the configured schedule.

Before deployment, read `docs/PRODUCTION_RUNBOOK.md` and run:

```powershell
python backend\manage.py check --deploy
python backend\manage.py production_check
python backend\manage.py learnloot_status
```

Production click-dedupe must use a shared Redis cache through
`LEARNLOOT_CACHE_URL`; the process-local cache remains a development fallback.
CMS media must live on persistent storage and be backed up separately from
PostgreSQL. The production check requires an explicit
`LEARNLOOT_MEDIA_PERSISTENCE_CONFIRMED=true` acknowledgement after that storage
and backup path is genuinely configured.

Health probes are available at `/api/health/live/` and
`/api/health/ready/`. The readiness endpoint returns HTTP 503 when the database is unavailable. A
cache outage is reported as HTTP 200 with `status=degraded` because the public
site can continue serving content while click-dedupe analytics are degraded. It
never exposes credentials or raw exception details.


## Phase 11 custom LearnLoot admin CMS

LearnLoot now has a branded custom admin at `http://localhost:3000/admin` backed by staff-only Django session APIs under `/api/admin/`. The original Django admin remains available only as an emergency fallback at `/django-admin/` on the backend.

The custom admin uses Material UI with a restrained 4px radius, responsive navigation, light/dark mode, course CMS editing, Shopee editorial post/product editing, SEO controls, click/publishing visibility, and a CMS media library. Scraped Udemy fields remain source-controlled while CMS overrides stay editable and persistent.

Rich article/course content uses self-hosted CKEditor 5 open-source plugins and image upload through the staff-only media endpoint. Server-side HTML is sanitized with `nh3` before it is stored. CKEditor 5 v44+ requires a self-hosting license key; the example frontend configuration uses `GPL`, which is appropriate only when your distribution complies with the GPL. Use a commercial self-hosting key otherwise.

Local custom-admin startup:

1. Start Django: `python backend\manage.py runserver`
2. Start Next.js: `cd frontend; npm run dev`
3. Create a staff account if needed: `python backend\manage.py createsuperuser`
4. Browse `http://localhost:3000/admin`

The local CORS/CSRF examples allow both `localhost:3000` and `127.0.0.1:3000`. Keep production origins explicit.
