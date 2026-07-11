# Production Deployment

This guide covers everything required to deploy Provena to a production environment. The current hosting model uses Render (API and workers) plus Vercel (frontend), with Cloudflare in front for DNS, TLS, and CDN. A Docker Compose self-hosted path is also documented for teams that want to own the infrastructure.

---

## Prerequisites

Before deploying, obtain credentials for all external services below.

### Required

| Service | What you need | Where to get it |
|---|---|---|
| **Stripe** | Secret key, publishable key, webhook signing secret | Stripe dashboard → Developers → API keys |
| **PostgreSQL** | Connection string `postgres://user:pass@host:5432/dbname` | Managed (Render Postgres, AWS RDS, Supabase) |
| **Redis** | Connection string `redis://:pass@host:6379/0` | Managed (Render Redis, AWS ElastiCache, Upstash) |
| **Django secret key** | 50+ character random string | See below |

**Generating a Django secret key**

Django's secret key must be a long, unpredictable string. Generate one with either of these (no external service needed):

```bash
# Requires Django installed (inside the provena-api venv)
python -c "from django.utils.crypto import get_random_string; print(get_random_string(50))"

# Pure Python — no dependencies
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Copy the output directly into `DJANGO_SECRET_KEY`. Never reuse a key across environments, and never commit it to git.

### Strongly Recommended

| Service | What you need | Notes |
|---|---|---|
| **Email (Resend, SendGrid, or AWS SES)** | SMTP host, port, user, password, from-address | Without this, no transactional emails are sent |
| **Sentry** | DSN for backend, DSN for frontend (can be same project) | Error tracking and performance monitoring |
| **Cloudflare** | Domain configured, TLS Full (strict) | DNS, TLS termination, CDN, DDoS protection |

### For Media Uploads

| Service | What you need |
|---|---|
| **AWS S3 or Cloudflare R2** | Access key ID, secret access key, bucket name, region |

Without this, product image and KYC document uploads will fail. Django falls back to `MEDIA_ROOT` (local disk) in development only.

---

## Environment Variables Reference

### Backend (`provena-api/.env` or host environment)

```env
# Required
DJANGO_SECRET_KEY=<50+ random chars>
DJANGO_ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com

# Database and cache
# App traffic goes through PgBouncer (transaction pooling); migrations use the
# direct connection. See "Connection pooling (PgBouncer)" below.
DATABASE_URL=postgres://user:pass@pgbouncer-host:6432/provena
DIRECT_DATABASE_URL=postgres://user:pass@db-host:5432/provena
REDIS_URL=redis://:pass@host:6379/0
# Self-hosted compose also reads DB_USER / DB_PASSWORD / DB_NAME (default: provena).

# Payments
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=465
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<api-key>
EMAIL_USE_SSL=True
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Storage
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=provena-media
AWS_S3_REGION_NAME=eu-west-2        # or auto for Cloudflare R2

# Monitoring
SENTRY_DSN=https://...@sentry.io/...

# Full-text search (Typesense). The self-host compose defaults TYPESENSE_HOST
# to the bundled `typesense` service, so search is ON by default there; set
# TYPESENSE_HOST="" to disable it and fall back to Postgres. On other hosting
# (no bundled service) an unset host disables search. Always override the API
# key in production. See "Full-text search (Typesense)" below.
TYPESENSE_HOST=typesense
TYPESENSE_PORT=8108
TYPESENSE_PROTOCOL=http
TYPESENSE_API_KEY=<generate a strong key; do not ship the compose default>

# Platform
FRONTEND_URL=https://yourdomain.com
PLATFORM_FEE_PERCENT=10             # default commission rate
DJANGO_SETTINGS_MODULE=config.settings.production
```

### Frontend (`provena-web/.env.local` or Vercel environment)

```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
NEXT_PUBLIC_SENTRY_DSN=https://...@sentry.io/...
```

---

## Option A: Docker Compose (Self-Hosted)

Use this path to run the entire stack on a VPS, dedicated server, or on-premise hardware.

### Server requirements

- 2 vCPU, 4 GB RAM minimum (4 vCPU, 8 GB recommended for production load)
- Ubuntu 22.04 LTS or Debian 12
- Docker Engine 24+, Docker Compose v2
- Ports 80 and 443 open (or 80 only if Cloudflare handles TLS termination)

### 1. Provision the server and install Docker

```bash
# On the server
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect
```

### 2. Deploy the application

```bash
git clone https://github.com/donolu/provena.git
cd provena

# Create production environment file
cp provena-api/.env.example provena-api/.env
# Edit .env with all production values (see Environment Variables above)

# Create web environment file
cat > provena-web/.env.production <<EOF
NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
NEXT_PUBLIC_SENTRY_DSN=...
EOF

# Build and start all services
docker compose up -d

# Apply database migrations
docker compose exec api sh -c 'DATABASE_URL="$DIRECT_DATABASE_URL" python manage.py migrate --no-input'

# Collect static files
docker compose exec api python manage.py collectstatic --no-input

# Create superuser (first deployment only)
docker compose exec api python manage.py createsuperuser
```

### 3. Verify the deployment

```bash
# Check all services are running
docker compose ps

# Check API health
curl http://localhost:8000/health

# Tail logs
docker compose logs -f api worker
```

### 4. Register the Stripe webhook endpoint

In the Stripe dashboard, add a webhook endpoint:
- URL: `https://api.yourdomain.com/api/v1/payments/webhook/`
- Events: `payment_intent.succeeded`, `payment_intent.payment_failed`, `checkout.session.completed`
- Copy the signing secret to `STRIPE_WEBHOOK_SECRET` in `.env`

### 5. Configure Cloudflare (recommended)

1. Add your domain to Cloudflare and point DNS to your server IP
2. Set SSL/TLS mode to **Full (Strict)**
3. Enable **Always Use HTTPS**
4. Enable **HTTP/3 (with QUIC)** for performance
5. Create a page rule to cache `/static/*` and `/media/*` at the CDN edge

The Nginx config proxies `/api/` to Django and `/` to Next.js. Nginx terminates connections on port 80; Cloudflare provides TLS.

### Updating to a New Release (zero-downtime)

Nginx balances across multiple `api` (and `web`) replicas via Docker DNS and retries any request that hits a just-started replica (`proxy_next_upstream` in `nginx/nginx.conf`). `scripts/deploy.sh` uses this to roll the app with no downtime window: it builds the new image, starts new replicas alongside the running ones, waits until they report healthy (`/api/v1/health/`), then retires the old ones.

```bash
git pull origin main

# 1. Apply backward-compatible (expand) migrations first, against the DIRECT
#    connection (migrations must not go through PgBouncer — see above).
docker compose exec api sh -c 'DATABASE_URL="$DIRECT_DATABASE_URL" python manage.py migrate --no-input'

# 2. Roll api and web to the new image, health-gated, one batch at a time.
scripts/deploy.sh            # or: scripts/deploy.sh api    /    TARGET_REPLICAS=3 scripts/deploy.sh
```

Deploy with `scripts/deploy.sh`, not `docker compose up` — the script manages the replica handover. Verified locally with thousands of requests through Nginx during a roll and zero failures.

**Expand/contract migrations.** During a roll the old and new code run **simultaneously**, so every schema change must stay compatible with the currently-deployed version:

- **Expand** (deploy first, safe): add nullable columns/tables, add indexes (`CREATE INDEX CONCURRENTLY`), add new code paths that tolerate old data.
- Deploy the new application version (`scripts/deploy.sh`).
- **Contract** (only in a *later* release, once the old version is fully retired): drop columns, enforce `NOT NULL`, remove old code.

Never ship an incompatible schema change in the same release that needs it — split it across two deploys.

---

## Option B: Render + Vercel (Current Hosting)

This is the setup described in [ADR-006](../provena-api/docs/DECISIONS.md). It is lower operational overhead than self-hosted but higher cost per compute unit.

### Backend on Render

1. Create a new **Web Service** from the `provena-api/` directory (or the monorepo root pointing to `provena-api/` as the root directory)
2. Runtime: **Docker** (uses `provena-api/Dockerfile`, `target: production`)
3. Add all backend environment variables in the Render dashboard
4. Create a managed **PostgreSQL** database on Render; copy the `DATABASE_URL` into the web service
5. Create a managed **Redis** instance; copy the `REDIS_URL`
6. Create a **Background Worker** for the Celery worker: same Docker image, command `celery -A config.celery worker --loglevel=info --concurrency=4`
7. Create a second **Background Worker** for Celery Beat: command `celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler`

Run migrations via Render's shell or by adding a deploy command:
```
python manage.py migrate --no-input && python manage.py collectstatic --no-input
```

### Frontend on Vercel

1. Import the `provena-web/` directory into Vercel (or the monorepo root, setting `provena-web` as the root directory)
2. Framework: **Next.js** (auto-detected)
3. Add all frontend environment variables in the Vercel project settings
4. Deploy

Vercel handles TLS, CDN, and automatic ISR revalidation. No Nginx is needed when using Vercel.

---

## Initial Data Setup

After first deployment, configure the platform:

```bash
# Log in to Django admin at https://api.yourdomain.com/admin/
# - Change the default superuser password
# - Add initial product categories (Catalogue → Categories)
# - Configure Celery Beat schedules (Periodic Tasks → Periodic Tasks)

# Or via management commands:
docker compose exec api python manage.py shell -c "
from apps.catalogue.models import Category
Category.objects.bulk_create([
    Category(name='Fresh Produce', slug='fresh-produce'),
    Category(name='Dry Goods', slug='dry-goods'),
    Category(name='Dairy', slug='dairy'),
])
print('Categories created')
"
```

---

## Connection pooling (PgBouncer)

The app connects to Postgres through **PgBouncer in transaction pooling mode**, so many API and worker processes multiplex a small pool of server connections (required before scaling beyond ~50 concurrent workers). The self-hosted `docker-compose.yml` runs an `edoburu/pgbouncer` sidecar; Render's managed Postgres provides PgBouncer itself.

Transaction pooling reassigns a server connection between transactions, so the Django settings disable the two things bound to a single backend:

- `DISABLE_SERVER_SIDE_CURSORS = True`
- psycopg server-side prepared statements (`OPTIONS = {"prepare_threshold": None}`)

These are applied automatically for Postgres and are harmless on a direct connection.

**Migrations must bypass the pooler** and use a direct Postgres connection (`DIRECT_DATABASE_URL`) — DDL, `CREATE INDEX CONCURRENTLY`, and advisory locks are unsafe under transaction pooling:

```bash
docker compose exec api sh -c 'DATABASE_URL="$DIRECT_DATABASE_URL" python manage.py migrate --no-input'
```

Inspect the pool live via the admin console (`ADMIN_USERS` includes the DB user):

```bash
docker compose exec api psql "postgres://<user>:<pass>@pgbouncer:6432/pgbouncer" -c "SHOW POOLS;"
```

## Full-text search (Typesense)

Product search uses **Typesense** for ranked, typo-tolerant results. The self-hosted `docker-compose.yml` runs a `typesense` service; the API and worker read it via `TYPESENSE_HOST`/`TYPESENSE_PORT`/`TYPESENSE_PROTOCOL`/`TYPESENSE_API_KEY`.

In the self-hosted compose, `TYPESENSE_HOST` defaults to the bundled `typesense` service, so **search is enabled by default** there; set `TYPESENSE_HOST=""` to turn it off. On hosting without a bundled service (e.g. Render), an unset host disables it. **Always override `TYPESENSE_API_KEY`** in production; the compose default (`devsearchkey`) is for local use only.

Search **degrades gracefully**: if `TYPESENSE_HOST` is unset, or Typesense is unreachable or returns an error, the API falls back to the Postgres `ILIKE` query and logs a warning. Browsing and filtering never stall on the search engine, so this is safe to enable incrementally.

Products are indexed automatically: a signal enqueues a Celery task on every product/variant save, publish, or archive. After first enabling search (or changing the schema), run a one-time full sync:

```bash
docker compose exec api python manage.py reindex_search
```

The index only holds ACTIVE products; drafts/archived products are removed from it automatically.

## Database Migrations in Production

Always run migrations before starting the new application version, against the **direct** connection (see above):

```bash
# Check what will be applied (dry run)
docker compose exec api sh -c 'DATABASE_URL="$DIRECT_DATABASE_URL" python manage.py migrate --plan'

# Apply
docker compose exec api sh -c 'DATABASE_URL="$DIRECT_DATABASE_URL" python manage.py migrate --no-input'
```

If a migration requires a table lock (adding a non-nullable column to a large table), schedule it during a maintenance window. Django's `SeparateDatabaseAndState` is available for zero-downtime column additions.

---

## Celery Beat Schedules

The following tasks are scheduled via Celery Beat. Confirm they are running by checking the Django admin under **Periodic Tasks**:

| Task | Schedule | Purpose |
|---|---|---|
| `release-expired-cart-reservations` | Every 5 minutes | Frees reserved stock from abandoned carts |
| `check-low-stock-levels` | Daily at 06:00 | Sends alerts to suppliers |
| `check-lot-expiry` | Daily at 06:00 | Alerts for lots expiring within 3 days |

If periodic tasks are not appearing in the admin, run:

```bash
docker compose exec api sh -c 'DATABASE_URL="$DIRECT_DATABASE_URL" python manage.py migrate django_celery_beat'
```

---

## Monitoring and Alerting

### Sentry

With `SENTRY_DSN` set, Sentry captures:
- All unhandled exceptions in Django (including Celery tasks)
- All unhandled exceptions in Next.js (via `global-error.tsx`)
- Performance traces (configured in `settings/production.py`)

Set up Sentry alerts for:
- Error frequency thresholds
- Performance regressions (P95 response time)
- Celery task failure rates

### Logs

Django writes structured JSON logs to stdout. Collect them with:
- **Render**: logs are available in the Render dashboard and can be forwarded to Papertrail or Datadog
- **Docker Compose**: `docker compose logs -f` or use a log driver (awslogs, gelf) in `docker-compose.yml`

### Health Check

Nginx exposes a health check endpoint at `/health` that returns `200 ok`. Use this for load balancer health checks.

---

## SSL and Security Headers

When running behind Cloudflare:
- Cloudflare terminates TLS; Nginx receives plain HTTP on port 80
- Set `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` in production settings (already configured)
- HSTS is applied by Django with `max-age=31536000; includeSubDomains; preload`

Django production settings also set:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

---

## AWS Migration Path

The current Render setup can be migrated to AWS without application code changes. The infrastructure equivalents are:

| Render / Vercel | AWS |
|---|---|
| Render Web Service (API) | ECS Fargate (task definition mirrors `docker-compose.yml`) |
| Render Background Worker (Celery) | ECS Fargate (separate task) |
| Render Managed PostgreSQL | RDS PostgreSQL 16 (multi-AZ for production) |
| Render Managed Redis | ElastiCache for Redis (cluster mode off, single node initially) |
| Vercel (Next.js) | ECS Fargate or AWS Amplify |
| Cloudflare (CDN) | CloudFront + ACM certificate |
| S3 / R2 (media) | S3 with CloudFront origin |

The migration is documented further in [provena-api/docs/TRD.md](../provena-api/docs/TRD.md) under the Infrastructure section.

---

## Backup Strategy

### Database

- **Render managed Postgres**: automated daily snapshots, 7-day retention (free tier). Increase to 30-day on paid plans.
- **Self-hosted**: configure `pg_dump` via cron:

```bash
# /etc/cron.daily/provena-backup
#!/bin/bash
docker compose exec db pg_dump -U provena provena | gzip > /backups/provena-$(date +%Y%m%d).sql.gz
find /backups -name "*.gz" -mtime +30 -delete
```

### Media Files

AWS S3 and Cloudflare R2 both provide 11-nines durability. Enable bucket versioning for additional protection.

### Secrets

Never commit secrets to git. Store them in:
- Render environment variables
- Vercel environment variables
- AWS Secrets Manager (AWS path)
- A `.env` file on the server, excluded from git (`provena-api/.env` is in `.gitignore`)
