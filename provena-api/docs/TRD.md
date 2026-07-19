# Technical Requirements Document

**Product:** Provena
**Version:** 1.1
**Status:** Living document (reflects shipped platform as of 2026-07)

> Change log
> - **1.1 (2026-07)** - corrected the stack versions, rewrote the API resource map and the data-model section to match the codebase (pricing pipeline, discounts, returns, platform-brokered delivery, refund-request ledger). See `DATABASE_SCHEMA.md` for the full model reference and `DECISIONS.md` for the ADRs.
> - **1.0** - initial draft.

---

## 1. System Overview

Provena is a two-tier web application:

- **Backend API** - Django REST Framework serving JSON over HTTPS; handles all business logic, data persistence, background jobs, and third-party integrations
- **Frontend** - Next.js (React, App Router, TypeScript) consuming the API; handles SSR for SEO-sensitive pages (product listings, catalogue) and CSR for authenticated dashboards

The two tiers communicate exclusively through the versioned REST API. They are deployed independently and can be scaled independently.

---

## 2. Technology Stack

### 2.1 Backend

| Component | Choice | Justification |
|---|---|---|
| Language | Python 3.12 | Stable, well-supported, strong ecosystem for web and data |
| Framework | Django 5.1 | Batteries-included ORM, auth, admin, migrations |
| API layer | Django REST Framework 3.17 | Industry standard for Django APIs; browsable API for development |
| API schema | drf-spectacular | OpenAPI 3 schema; TypeScript types generated for the frontend |
| Auth tokens | djangorestframework-simplejwt | JWT access + refresh tokens with rotation; refresh token in an HttpOnly cookie |
| Realtime | Django Channels + Redis | WebSocket order-status updates |
| Task queue | Celery 5 + Redis | Async jobs: order emails, payout triggers, low-stock alerts |
| Task scheduler | django-celery-beat | Cron-style scheduled tasks (expiry checks, reports) |
| Database | PostgreSQL 16 | ACID compliance, JSONB for flexible attributes, full-text search |
| Connection pooling | PgBouncer (transaction mode) | Pooled runtime connection; migrations use a direct connection (ADR-010) |
| Search | Typesense (optional) | Product search when enabled; thin wrapper no-ops otherwise |
| Cache | Redis | Session data, rate-limit counters, cart reservation locks, Channels layer |
| File storage | AWS S3 or Cloudflare R2 | Product images, KYC documents, report exports |
| Email | Resend (SMTP) | Transactional email with delivery tracking |
| Payments | Stripe API + Stripe Connect | PCI DSS handled by Stripe; Connect for supplier payouts |
| HTTP server | Gunicorn + Nginx | Gunicorn as WSGI worker; Nginx as reverse proxy and TLS terminator |
| Static files | WhiteNoise | Serves Django static files without a separate CDN in early stage |
| Linting | Ruff | Fast Python linter and formatter |
| Type checking | mypy (strict) | Catches type errors before runtime |
| Testing | pytest + pytest-django | Unit and integration tests |
| Containerisation | Docker | Consistent environments across dev and prod |

### 2.2 Frontend

| Component | Choice | Justification |
|---|---|---|
| Language | TypeScript 5 | Type safety across the entire frontend codebase (API types generated from the OpenAPI schema) |
| Framework | Next.js 16 (App Router) | SSR for SEO; RSC for performance; single-origin behind Nginx in production |
| Styling | Tailwind CSS 3 | Utility-first; no CSS bloat; consistent design system |
| State | Zustand | Lightweight global state (cart, auth) |
| Data fetching | TanStack Query v5 | Server state, caching, invalidation |
| Forms | React Hook Form + Zod | Performant forms with schema validation |
| UI components | shadcn/ui | Accessible, unstyled-base components built on Radix UI |
| HTTP client | Axios with interceptors | Token refresh logic in one place |
| Linting | ESLint + Prettier | Code quality and formatting |
| Testing | Vitest + React Testing Library | Unit and component tests |

### 2.3 Infrastructure

| Component | Choice | Justification |
|---|---|---|
| Container orchestration | Docker Compose (dev), Render/Railway (prod) | Simple enough for solo operator; upgradeable to Kubernetes |
| CI/CD | GitHub Actions | Already in use; free for public repos |
| DNS and CDN | Cloudflare | Free DDoS protection, TLS termination, caching |
| Monitoring | Sentry (errors) + Grafana + Prometheus | Full observability stack |
| Log aggregation | Loki (self-hosted) or Papertrail | Centralised logs searchable by request ID |
| Secret management | Environment variables (dev); provider secrets store (prod) | No secrets in code or Docker images |

---

## 3. API Design

### 3.1 Principles

- RESTful resources; plural nouns; no verbs in paths
- All endpoints versioned under `/api/v1/`
- JSON request and response bodies
- ISO 8601 dates (`2026-06-30T14:00:00Z`)
- Consistent error format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable summary",
    "fields": {
      "email": ["Enter a valid email address."]
    }
  }
}
```

- Pagination via `?page=` and `?page_size=` (max 100); metadata in response:

```json
{
  "count": 342,
  "next": "/api/v1/products/?page=3",
  "previous": "/api/v1/products/?page=1",
  "results": [...]
}
```

### 3.2 Resource Map

All resources are mounted under `/api/v1/`. The map below is grouped by domain (Django app); it lists the base paths and principal operations rather than every sub-route. The authoritative, always-current contract is the OpenAPI schema at `/api/v1/schema/` (Swagger UI and ReDoc served alongside).

**Auth and accounts** (`/auth/`)
| Path | Purpose |
|---|---|
| `login/`, `register/`, `logout/` | Session lifecycle; login returns an access token + sets the HttpOnly refresh cookie |
| `refresh/` | Rotates the refresh token from the HttpOnly cookie (no token in the body) |
| `me/` | Get/update the current user; `DELETE` requests GDPR erasure (anonymisation) |
| `totp/enable/`, `totp/verify/`, `totp/disable/` | Two-factor (TOTP) enrolment and verification |
| `password/reset/`, `password/reset/confirm/` | Password reset by emailed token |
| `addresses/` | Buyer saved delivery addresses (CRUD) |
| `data-export/` | Request/download a GDPR Article 20 data export (time-limited link) |

**Suppliers** (`/suppliers/`)
| Path | Purpose |
|---|---|
| `register/`, `me/`, `me/documents/`, `me/performance/` | Self-registration, profile (incl. shipping policy, VAT number, fulfilment mode), KYC docs, performance stats |
| `me/stripe-connect/` | Stripe Connect onboarding link |
| `` (list), `{slug}/` | Public approved-supplier list and detail |
| `admin/`, `admin/{id}/approve|suspend|reject/`, `admin/documents/{id}/review/` | Admin onboarding queue and KYC review |

**Catalogue** (`/catalogue/`): `categories/`, `products/` (+ `{slug}/`, `{slug}/variants/`), `search/`, `banners/`, featured. Public reads; supplier/admin writes.

**Inventory** (`/inventory/`): stock levels, `{id}/adjust/`, lots, and movement audit trail (supplier/admin).

**Marketplace** (`/marketplace/`): `cart/`, `cart/items/{id}/`, `wishlist/`, product `reviews/` (verified-purchase gated).

**Orders** (`/orders/`)
| Path | Purpose |
|---|---|
| `` (GET/POST), `{reference}/` | Buyer places and views orders |
| `{reference}/cancel/` | Cancel before dispatch (releases stock) |
| `{reference}/sub-orders/{id}/dispatch|deliver/` | Supplier fulfilment transitions |
| `{reference}/sub-orders/{id}/return/` | Buyer requests a return (optionally per-item) |
| `supplier/returns/`, `supplier/returns/{id}/approve|reject/` | Supplier return handling |
| `admin/returns/`, `admin/returns/{id}/refund/` | Admin processes an approved return refund |
| `admin/{reference}/refund-items/` | Admin refunds selected items; reverses the selling supplier's payout |
| `admin/`, `admin/{reference}/` | Admin order list and detail |
| `ws-ticket/` | Short-lived ticket for the order-status WebSocket |

**Discounts** (`/discounts/`): `validate/` (buyer cart preview), `admin/` and `admin/{id}/` (code CRUD).

**Payments** (`/payments/`)
| Path | Purpose |
|---|---|
| `create-intent/` | Creates the Stripe PaymentIntent for a pending order (returns `client_secret`) |
| `webhook/` | Stripe webhook (signature-verified): payment success/failure, refunds, Connect account updates |
| `` (list), `{reference}/` | Buyer payment history |
| `payouts/`, `admin/payouts/`, `admin/payouts/{id}/process/` | Supplier/admin payouts |
| `admin/payments/{id}/refund/`, `admin/payments/` | Admin amount-based (goodwill) refund and payment list |

**Delivery** (`/delivery/`): courier status `webhook/` and an admin reconciliation summary (ADR-013).

**Disputes** (`/disputes/`): `` (list/create), `{id}/`, `{id}/respond|escalate|resolve|close/`, `{id}/messages/`, `{id}/attachments/`, `admin/`, `admin/{id}/refund/`.

**Notifications** (`/notifications/`): list, mark-read, and per-event email `preferences/`.

**Analytics** (`/analytics/`): `dashboard/` (admin KPIs).

### 3.3 Authentication Flow

1. Client `POST /api/v1/auth/login/` with `email` + `password`
2. Server returns `access_token` (15min) + `refresh_token` (30 days)
3. Client sends `Authorization: Bearer <access_token>` on all subsequent requests
4. On 401, client `POST /api/v1/auth/refresh/` with `refresh_token`
5. Server returns new pair; old refresh token is invalidated (rotation)

### 3.4 Rate Limiting

| Client type | Limit |
|---|---|
| Anonymous | 100 requests per hour |
| Authenticated Buyer | 1,000 requests per hour |
| Authenticated Supplier | 2,000 requests per hour |
| Admin | No limit |
| Stripe webhook endpoint | IP allowlist only; no rate limit |

---

## 4. Data Architecture

### 4.1 Database

Single PostgreSQL 16 instance with connection pooling via PgBouncer.

Separate schemas per domain are not used (adds overhead); instead, app-prefixed table names (`accounts_user`, `catalogue_product`, etc.) are used through Django's standard convention.

UUID primary keys on all user-facing resources (prevents enumeration attacks). Sequential integer PKs for internal/join tables.

### 4.2 Domain Models (High Level)

Field-level detail, enums, and the entity-relationship diagram are in `DATABASE_SCHEMA.md`. Summary by app:

**accounts:** `User` (UUID, email, role BUYER/SUPPLIER/ADMIN, totp_enabled, `erased_at`), `AuditLog` (append-only admin-action log), `Address`, `DataExportRequest` (GDPR Article 20), `PasswordResetToken`.

**suppliers:** `Supplier` (business profile, `status`, `commission_rate`, VAT registration, **shipping policy** fields, **fulfilment_mode** + `platform_delivery_fee`, Stripe Connect), `SupplierAddress`, `SupplierDocument` (KYC).

**catalogue:** `Category` (self-referential tree, `dispute_window_days`), `Product` (+ **`vat_rate`**), `ProductVariant` (`price`, `sku`, `weight_grams`), `ProductImage`, `VariantImage`, `Banner`.

**inventory:** `StockLevel` (`quantity_available`, `quantity_reserved`, `low_stock_threshold`), `StockLot` (lot/expiry), `StockMovement` (audit trail).

**marketplace:** `Cart`, `CartItem`, `CartReservation` (TTL stock hold), `WishlistItem`, `Review` (verified-purchase gated).

**orders:** `Order` and `SubOrder` both carry the **pricing breakdown** (`goods_subtotal`, `discount_amount`, `shipping_amount`, `vat_amount`, total); `OrderItem` snapshots `unit_price`, `vat_rate`, `vat_amount`; `OrderReturn` + `ReturnItem` (per-item returns); `DiscountCode` + `DiscountRedemption` (funding PLATFORM/SUPPLIER, usage caps).

**payments:** `Payment` (Stripe PaymentIntent, `refunded_amount`, `pending_refund_amount`), `Payout` (per sub-order; `gross`/`platform_fee`/`net`, status incl. REVERSED), `PaymentRefundRequest` (idempotency ledger for refunds).

**delivery:** `CourierDelivery` (per sub-order; provider, quote/delivery ids, `fee_charged` vs `courier_cost`, status, tracking, quote expiry) - the reconciliation ledger for platform-brokered delivery (ADR-013).

**disputes:** `Dispute` (sub-order, parties, type, status, outcome, `payout_held`, response deadline), `DisputeEvent` (append-only), `DisputeMessage`, `DisputeAttachment`, `DisputeRefund`.

**notifications:** `Notification` (per recipient, typed, read/unread), `NotificationPreference` (per-event email toggles).

### 4.3 Caching Strategy

| Data | TTL | Backend |
|---|---|---|
| Product catalogue pages | 5 minutes | Redis |
| Category tree | 1 hour (bust on Admin change) | Redis |
| User session / JWT blocklist | 30 days | Redis |
| Cart reservation locks | 30 minutes | Redis |
| Rate limit counters | 1 hour rolling | Redis |

---

## 5. Security Requirements

Full detail in `COMPLIANCE.md`. Summary of technical controls:

- HTTPS enforced; HSTS preload; TLS 1.2 minimum, 1.3 preferred
- `SECRET_KEY` and all credentials injected via environment variables; never hardcoded
- Django's `SECURE_*` settings enabled in production
- CORS restricted to known frontend origins
- CSRF protection on all cookie-authenticated endpoints
- Object-level permissions: users can only access their own resources (enforced in DRF views)
- SQL injection prevented by ORM-only queries; raw SQL forbidden except in migrations
- File uploads: extension and MIME-type allowlist; files stored on S3, not served by Django
- Stripe webhook signature verified on every event (`stripe.Webhook.construct_event`)
- Passwords: bcrypt with cost factor 12
- PII fields encrypted at rest using field-level encryption for documents

---

## 6. Background Tasks (Celery)

| Task | Trigger | Description |
|---|---|---|
| `send_order_confirmation` | Order confirmed | Email to buyer and supplier |
| `reserve_stock` | Item added to cart | Decrement available stock; set 30-minute TTL |
| `release_stock_reservation` | Cart abandoned / TTL expired | Return reserved quantity |
| `trigger_payout` | Order delivered | Transfer supplier net amount via Stripe Connect |
| `check_low_stock` | Daily cron | Alert suppliers below threshold |
| `check_lot_expiry` | Daily cron | Alert suppliers of lots expiring within N days |
| `generate_daily_report` | Daily cron | Aggregate sales and inventory report for Admin |
| `cleanup_expired_carts` | Hourly cron | Remove abandoned carts older than 48 hours |

---

## 7. Testing Strategy

| Layer | Tool | Scope |
|---|---|---|
| Unit | pytest + pytest-django | Model methods, serialiser validation, utility functions |
| Integration | pytest with real DB (test transaction rollback) | API endpoints, Celery tasks, Stripe webhook handler |
| Security | Bandit (SAST), Safety (dep scan), OWASP ZAP (DAST) | Run in CI |
| Load | Locust | Before each major release; not in standard CI |
| End-to-end | Playwright (frontend) | Critical paths: registration, checkout, order tracking |

Coverage target: 80% minimum across all apps.

---

## 8. Environment Configuration

All configuration via environment variables using `django-environ`.

```
# Core
DJANGO_SECRET_KEY=
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=

# Database
DATABASE_URL=postgres://user:pass@host:5432/provena

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=eu-west-2

# Stripe
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@provena.io

# Sentry
SENTRY_DSN=

# Frontend
FRONTEND_URL=https://provena.io
```

---

## 9. Infrastructure and Deployment

### Development

Docker Compose runs: Django API, PostgreSQL, Redis, Celery worker, Celery beat.

```bash
docker compose up
```

All services available locally; no external services required for basic development.

### Production (initial)

| Service | Provider |
|---|---|
| API | Render (web service; auto-deploy from `main`) |
| Frontend | Vercel or Render |
| PostgreSQL | Render managed Postgres or Supabase |
| Redis | Render Redis or Upstash |
| File storage | Cloudflare R2 (S3-compatible, cheaper egress) |
| Email | SendGrid free tier initially |
| Error tracking | Sentry (free tier) |
| CDN and DNS | Cloudflare |

### Production (scaled)

When traffic warrants it, migrate to:

- AWS ECS (Fargate) or Kubernetes for the API
- AWS RDS PostgreSQL Multi-AZ
- AWS ElastiCache Redis cluster
- CloudFront CDN in front of S3

The application code does not need to change for this migration; only infrastructure configuration changes.
