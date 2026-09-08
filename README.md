# LearnLoot Course Deals Platform

## Stack

- Django + Django REST Framework
- PostgreSQL
- Redis + Celery
- Scrapy + scrapy-playwright
- Next.js + React + TypeScript + Tailwind CSS

## Local infrastructure

```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

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