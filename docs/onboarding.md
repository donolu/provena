# Developer Onboarding

This guide gets a new developer running Provena locally, understanding the codebase layout, and making their first change. Two paths are covered: Docker Compose (recommended for a full-stack environment) and bare-metal (recommended when you are working on one layer only).

---

## Prerequisites

| Tool | Minimum Version | Notes |
|---|---|---|
| Git | 2.38+ | `git --version` |
| Docker Desktop | 4.x | Includes Docker Compose v2 |
| Python | 3.12 | For bare-metal API work; `python3 --version` |
| Node.js | 20 LTS | For bare-metal web work; `node --version` |
| npm | 10+ | Comes with Node 20 |

**Accounts you will need:**
- Stripe account (free test mode) — for payment flows
- Sentry account (optional) — for error tracking; omit the DSN to disable
- AWS/Cloudflare R2 account (optional) — for media uploads; local dev can skip this

---

## 1. Clone the Repo

```bash
git clone https://github.com/donolu/provena.git
cd provena
```

---

## 2. Path A: Docker Compose (Recommended)

This runs the full stack — PostgreSQL, Redis, Django API, Celery worker, Celery Beat, Next.js, and Nginx — in one command.

### 2a. Configure environment

```bash
cp provena-api/.env.example provena-api/.env
cp provena-web/.env.example provena-web/.env.local
```

Open `provena-api/.env` and fill in at minimum:

```env
DJANGO_SECRET_KEY=any-long-random-string-for-local-dev
STRIPE_SECRET_KEY=sk_test_...       # from Stripe dashboard → Developers → API keys
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...     # from Stripe CLI: stripe listen --print-secret
```

Open `provena-web/.env.local` and fill in:

```env
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### 2b. Start all services

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

The first run downloads images and builds both Dockerfiles. This takes 3-5 minutes. Subsequent starts are fast.

### 2c. Apply migrations and create a superuser

```bash
# In a separate terminal (leave the compose stack running)
docker compose exec api python manage.py migrate
docker compose exec api python manage.py createsuperuser
```

### 2d. Verify

| URL | Service |
|---|---|
| `http://localhost:3000` | Next.js frontend |
| `http://localhost:8000/api/v1/` | Django API root |
| `http://localhost:8000/admin/` | Django admin (superuser credentials) |
| `http://localhost:8000/api/schema/swagger-ui/` | OpenAPI docs |

### Common Docker commands

```bash
# Tail logs for a specific service
docker compose logs -f api

# Run a Django management command
docker compose exec api python manage.py shell

# Run migrations after pulling new code
docker compose exec api python manage.py migrate

# Rebuild after Dockerfile or dependency changes
docker compose build api
docker compose build web
```

---

## 3. Path B: Bare-Metal

Use this when you want faster iteration on a single layer.

### 3a. Backend

```bash
cd provena-api

# Create and activate a virtual environment
python3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install all dependencies including dev tools
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env — see section 2a above

# Start PostgreSQL and Redis (quickest option: via Docker)
docker run -d --name provena-db -e POSTGRES_DB=provena -e POSTGRES_USER=provena \
  -e POSTGRES_PASSWORD=provena -p 5432:5432 postgres:16-alpine
docker run -d --name provena-redis -p 6379:6379 redis:7-alpine

# Apply migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Start the API
python manage.py runserver
```

```bash
# In a second terminal: start Celery worker
source venv/bin/activate
celery -A config.celery worker --loglevel=info

# In a third terminal: start Celery Beat (scheduled tasks)
source venv/bin/activate
celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 3b. Frontend

```bash
cd provena-web
npm install
cp .env.example .env.local
# Edit .env.local

npm run dev
```

The dev server has hot module reload. Most changes reflect without a restart.

---

## 4. Install Git Hooks

Run this once per clone from the repo root:

```bash
# Requires pre-commit (already in the API venv, or install globally)
provena-api/venv/bin/pre-commit install
# Or if pre-commit is globally available:
pre-commit install
```

On every `git commit`, pre-commit will run:
- `ruff` — Python linting and auto-fix on `provena-api/` files
- `ruff-format` — Python formatting on `provena-api/` files
- `bandit` — Python security SAST on `provena-api/` files
- Trailing whitespace, end-of-file, YAML, TOML checks on all files

---

## 5. Running Tests

### Backend

```bash
cd provena-api
source venv/bin/activate  # if not already active

# All tests with coverage report
pytest

# Single app
pytest apps/orders/

# Single file
pytest apps/orders/tests/test_services.py

# With verbose output
pytest -v

# Minimum 80% coverage is enforced; CI fails below this threshold
```

### Frontend

```bash
cd provena-web

# Unit tests (Vitest + React Testing Library)
npm run test:unit

# Unit tests in watch mode (during development)
npm run test:unit:watch

# End-to-end tests (Playwright; requires a running backend at localhost:8000)
npm run test:e2e
```

E2E tests skip gracefully when `TEST_USER_EMAIL` and `TEST_USER_PASSWORD` environment variables are not set.

---

## 6. Linting and Type Checking

### Backend

```bash
cd provena-api
source venv/bin/activate

# Lint and auto-fix
ruff check apps/ --fix

# Format
ruff format apps/

# Type check (Django + DRF stubs)
mypy apps/

# Security SAST
bandit -r apps/ -c pyproject.toml

# Dependency CVE scan
safety check
```

### Frontend

```bash
cd provena-web

# ESLint (zero warnings policy)
npm run lint

# TypeScript type check
npm run type-check
```

---

## 7. Codebase Orientation

### Django API (`provena-api/`)

The API is a **modular monolith**: one Django process containing eight domain apps. The design rule is that inter-domain calls happen only through `services.py` — never direct model imports between apps. This keeps each domain independently extractable if needed.

**Domain apps:**

| App | Responsibility | Key models |
|---|---|---|
| `accounts` | Auth, users, 2FA, rate limiting, audit log | `User`, `AuditLog` |
| `suppliers` | Vendor onboarding, KYC review | `Supplier`, `SupplierDocument` |
| `catalogue` | Products, categories, banners | `Category`, `Product`, `ProductVariant`, `Banner` |
| `inventory` | Stock levels, lot tracking, movement audit | `StockLevel`, `StockLot`, `StockMovement` |
| `marketplace` | Cart, wishlist, reviews | `Cart`, `CartItem`, `WishlistItem`, `Review` |
| `orders` | Order lifecycle, disputes, returns | `Order`, `SubOrder`, `OrderDispute`, `OrderReturn` |
| `payments` | Stripe integration, payouts | `Payment`, `Payout` |
| `notifications` | In-app and email | `Notification`, `NotificationPreference` |
| `analytics` | Reports (read-only, no models) | — |

**Key conventions:**

- `models.py` — data layer only; no business logic
- `services.py` — business logic; called by views and tasks; calls other apps' `services.py` if needed
- `serializers.py` — request/response shape; read serializers may differ from write serializers
- `views.py` — thin; delegates to services
- `tasks.py` — Celery tasks; always have retry logic and Sentry capture
- `permissions.py` — custom DRF permission classes per domain
- `tests/` — mirrors the structure above; factories in `tests/factories.py`

**Finding your way around:**

- All API URLs: `config/urls.py` includes each app's `urls.py`
- All settings: `config/settings/base.py` (shared), `development.py` (local), `production.py` (live)
- Celery task schedule: `CELERY_BEAT_SCHEDULE` in `config/settings/base.py`

### Next.js Frontend (`provena-web/`)

The frontend uses the **App Router** with route groups. Route groups (`(buyer)`, `(supplier)`, `(admin)`) share layouts without affecting the URL.

**Route tree summary:**

```
/                          Homepage (banners, featured products, hero)
/catalogue/                Product listing (SSR + ISR, revalidate=60)
/catalogue/[slug]/         Product detail (SSR + generateStaticParams)
/(auth)/login/             Login
/checkout/                 Cart and Stripe Checkout
/orders/[reference]/       Order detail
/account/payments/         Buyer payment history
/account/notifications/    Notification feed
/account/security/         2FA setup and management
/supplier/dashboard/       Supplier overview
/supplier/products/        Product management
/supplier/inventory/       Stock management
/supplier/orders/          Order fulfilment
/supplier/payouts/         Payout ledger
/admin/dashboard/          Analytics dashboard
/admin/suppliers/          Supplier review and commission
/admin/users/              User management
/admin/orders/             Order oversight
/admin/disputes/           Dispute resolution
/admin/returns/            Return management
/admin/banners/            Homepage banner management
/admin/audit-log/          Admin action log
/admin/analytics/          Revenue reports and CSV export
```

**Key conventions:**

- Server components by default; `'use client'` only when interactivity or browser APIs are needed
- `src/lib/api/` — all HTTP calls; return typed responses; never call `fetch` directly in components
- Auth state lives in `src/store/auth.ts` (Zustand); sets `has_session`, `user_role`, `totp_enabled` cookies
- Middleware (`src/middleware.ts`) guards routes by role and TOTP enrolment
- All forms use `react-hook-form` + `zod` schemas

---

## 8. Making Your First Change

### Adding a new API endpoint

1. Add the business logic to `apps/<domain>/services.py`
2. Add (or extend) the serializer in `apps/<domain>/serializers.py`
3. Add the view in `apps/<domain>/views.py` — use an existing view as a template
4. Register the URL in `apps/<domain>/urls.py`
5. Write a test in `apps/<domain>/tests/test_views.py`
6. Run `pytest apps/<domain>/` to verify

### Adding a new frontend page

1. Create `src/app/<route>/page.tsx`
2. Add API call functions to `src/lib/api/<domain>.ts`
3. If the route needs auth, check middleware covers it (admin/supplier routes are already guarded)
4. Run `npm run lint && npm run type-check` before committing

---

## 9. Stripe Webhook During Local Development

Stripe webhooks need to reach your local server. Use the Stripe CLI:

```bash
# Install Stripe CLI (macOS)
brew install stripe/stripe-cli/stripe

# Log in
stripe login

# Forward webhooks to local API
stripe listen --forward-to localhost:8000/api/v1/payments/webhook/

# The CLI prints the webhook signing secret — copy it to .env as STRIPE_WEBHOOK_SECRET
```

---

## 10. Troubleshooting

**`django.db.OperationalError: could not connect to server`**
Postgres is not running. Start it with Docker: `docker start provena-db` or `docker compose up db`.

**`redis.exceptions.ConnectionError`**
Redis is not running. `docker start provena-redis` or `docker compose up redis`.

**`ModuleNotFoundError` after pulling new code**
New Python dependencies were added. Run `pip install -e ".[dev]"` inside the venv.

**`npm ERR! missing script: type-check`**
You have a stale `node_modules` from before the `type-check` script was added. Run `npm install` again.

**Migrations out of sync**
```bash
python manage.py showmigrations    # see which are not applied
python manage.py migrate           # apply all pending
```

**Pre-commit hook failing on ruff**
```bash
ruff check apps/ --fix             # auto-fix what can be auto-fixed
ruff format apps/                  # reformat
git add -u                         # re-stage fixed files
git commit                         # retry
```

**TOTP enforcement redirect loop**
If you are redirected to `/account/security` on every page load, your account's TOTP is not enrolled. Log in to the Django admin, find your User record, and set `totp_enabled=True` temporarily for testing, or complete the TOTP setup flow.
