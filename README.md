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
