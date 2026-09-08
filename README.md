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

## Admin discovery operations

1. Create or verify the `Udemy` provider with slug `udemy`.
2. Keep the provider Active.
3. Confirm the Provider admin reports discovery as `Ready`.
4. Select the provider and choose **Queue discovery for selected providers**.
5. Inspect Discovery Runs, observations, courses, sources, and price history in
   Django admin.

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

## Phase 7 Telegram publication delivery

Phase 7 consumes `publication_queue` through Celery and records Telegram
delivery state, attempt counts, timestamps, and the sent message id in
`telegram_posts`. Telegram publication is disabled by default. Set
`LEARNLOOT_TELEGRAM_ENABLED=true` only after configuring the bot token, target
chat/channel, and `LEARNLOOT_PUBLIC_BASE_URL`.

Telegram messages link to the LearnLoot landing route
`/courses/<provider-slug>/<course-slug>` rather than linking directly to the
provider. The public frontend for that route is implemented in a later phase.

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

No bot token or raw Telegram destination is stored in the database. Delivery
records store only a keyed SHA-256 target fingerprint, rendered message snapshot,
LearnLoot landing URL, message id, attempts, timestamps, and sanitized errors.
