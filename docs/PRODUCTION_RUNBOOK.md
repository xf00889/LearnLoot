# LearnLoot Production Runbook

Phase 10 keeps local Windows development on EnvKit PostgreSQL + Redis and adds
production checks without forcing Docker.

## Required production services

Run separate supervised processes for:

1. Django web/API application behind HTTPS/reverse proxy.
2. Next.js frontend.
3. PostgreSQL.
4. Redis.
5. Celery worker.
6. Exactly one Celery beat scheduler.

Celery documents that only one scheduler should own a periodic schedule at a
time; multiple beat instances can enqueue duplicate work.

## Production environment

Start from `.env.example`, keep real secrets outside Git, and set at minimum:

- `LEARNLOOT_ENVIRONMENT=production`
- `DJANGO_DEBUG=false`
- a strong `DJANGO_SECRET_KEY`
- explicit production `DJANGO_ALLOWED_HOSTS`
- production PostgreSQL `DATABASE_URL`
- production Redis broker/result URLs
- `LEARNLOOT_CACHE_URL` using a separate Redis logical DB/instance
- HTTPS `LEARNLOOT_PUBLIC_BASE_URL`
- secure cookie/SSL/HSTS settings
- persistent `LEARNLOOT_MEDIA_ROOT`
- `LEARNLOOT_MEDIA_PERSISTENCE_CONFIRMED=true` only after media durability and
  backups are actually configured

If a reverse proxy terminates TLS, set `DJANGO_TRUST_X_FORWARDED_PROTO=true`
only when that proxy strips any client-supplied `X-Forwarded-Proto` header and
sets the trusted value itself.

Before release:

```powershell
python backend\manage.py check
python backend\manage.py check --deploy
python backend\manage.py production_check
python backend\manage.py migrate --check
python -m pytest backend
```

## Health endpoints

- `/api/health/live/` proves the Django process can answer HTTP.
- `/api/health/ready/` checks the database and configured Django cache.
- `/api/health/` remains the backward-compatible database health endpoint.

All health responses are `no-store`. The readiness route returns HTTP 503 when the database is unavailable. Cache
failure is reported as a degraded HTTP 200 because it affects shared dedupe
accuracy rather than core page availability. Responses do not return credentials
or exception text.

Use liveness for process restart decisions and readiness for load-balancer
traffic decisions.

## Shared Redis cache

Course and shopping click dedupe uses Django's cache. Development may use the
process-local cache, but production must configure `LEARNLOOT_CACHE_URL` so
multiple web processes share the same short-lived dedupe keys.

Use a cache database/instance separate from Celery's result backend when
practical.

## Celery automation

Automation is off by default. After provider access and production services are
verified:

```env
LEARNLOOT_AUTOMATION_ENABLED=true
LEARNLOOT_DISCOVERY_INTERVAL_MINUTES=60
LEARNLOOT_DISCOVERY_RUNNING_STALE_MINUTES=90
LEARNLOOT_TELEGRAM_MAINTENANCE_INTERVAL_MINUTES=5
```

Run one worker and exactly one beat scheduler. Example Linux-style commands:

```text
celery -A config --workdir backend worker --loglevel=INFO
celery -A config --workdir backend beat --loglevel=INFO --schedule /var/lib/learnloot/celerybeat-schedule
```

On Windows development, continue using the worker `--pool=solo`; production
process management should use the deployment platform's supported worker model.

The periodic discovery scheduler skips inactive/not-ready providers and avoids
queuing a second run while a recent `RUNNING` discovery exists.

## Operational status

For a secret-free CLI snapshot:

```powershell
python backend\manage.py learnloot_status
```

It reports database/cache health, course counts, latest discovery state,
publication queue/Telegram failure counts, shopping publication counts, and
click-event totals. It never prints database URLs, Telegram tokens, or secret
keys.

## PostgreSQL backups

Create a custom-format backup:

```powershell
python backend\manage.py backup_postgres --output "D:\backups\learnloot\learnloot-2026-09-09.dump"
```

Verify the archive is readable:

```powershell
python backend\manage.py verify_postgres_backup "D:\backups\learnloot\learnloot-2026-09-09.dump"
```

The backup command passes the database password to `pg_dump` through the child
process environment rather than a command-line argument and never prints it.

A readable archive is not a complete restore test. Regularly restore a backup
into a disposable PostgreSQL database and run Django checks against that
database before calling the backup strategy verified.

Keep database backups outside the Git repository and apply retention/encryption
appropriate to the hosting environment.

## CMS media backups

Course editorial images, social images, shopping cover images, and product
images are independent of PostgreSQL. Database backup alone is therefore
insufficient.

For the current FileSystemStorage implementation, production must place
`MEDIA_ROOT` on persistent storage and back up that storage on a schedule aligned
with database backups. Test restoration of both the database and media together.

Do not set `LEARNLOOT_MEDIA_PERSISTENCE_CONFIRMED=true` merely to silence the
production check.

## HTTPS and security headers

Django's security middleware handles backend HTTPS redirect, secure cookies,
HSTS, content-type sniffing protection, referrer policy, and frame denial using
the Phase 10 environment settings.

The public Next.js application should also receive HTTPS and browser security
headers at the hosting/reverse-proxy layer. Do not blindly enable
`SECURE_PROXY_SSL_HEADER`; Django documents that it is safe only when the proxy
is controlled and sanitizes the forwarded header.

Start HSTS with a conservative duration after HTTPS is confirmed. Increase it,
include subdomains, and enable preload only after verifying every affected
subdomain can remain HTTPS-only.

## Static and media serving

Run `collectstatic` for backend admin/static assets:

```powershell
python backend\manage.py collectstatic --noinput
```

Django development media serving remains DEBUG-only. Production must serve
`MEDIA_URL` through the persistent media service/reverse proxy/CDN rather than
through Django.

## Release gate

A production release is accepted only after:

- `production_check` passes with production settings;
- `check --deploy` is reviewed and passes at the chosen failure threshold;
- migrations are fully applied;
- backend tests pass;
- frontend lint/type/build checks pass in the deployment environment;
- liveness/readiness probes pass through the real HTTPS route;
- a PostgreSQL backup is created, verified, and periodically restore-tested;
- persistent CMS media is backed up and restore-tested;
- one Celery beat scheduler and the intended worker count are supervised;
- Telegram remains disabled until the public LearnLoot URL and channel
  permissions are verified.
