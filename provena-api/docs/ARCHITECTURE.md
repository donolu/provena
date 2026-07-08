# Architecture

**Product:** Provena
**Version:** 1.0
**Pattern:** Modular Monolith (API) + Decoupled Frontend

---

## 1. Guiding Principle

Provena starts as a **modular monolith**: one Django application with strict domain boundaries between apps, deployed as a single process. This is not a shortcut. It is the correct architecture for a product at this stage.

Each domain app (accounts, catalogue, inventory, orders, payments, suppliers, notifications, analytics) is designed so that it can be extracted as an independent service when scale or team size demands it. The inter-domain contracts are defined through service layer calls and serialised data, not direct model imports across domain boundaries.

This approach avoids the operational overhead of microservices (distributed tracing, network latency between services, complex deployment pipelines) until that overhead is justified by actual scale.

---

## 2. High-Level Architecture

```
                          ┌─────────────────────────────────────┐
                          │           Cloudflare CDN             │
                          │        (DNS, TLS, DDoS, Cache)       │
                          └────────────┬──────────────┬──────────┘
                                       │              │
                          ┌────────────▼──┐  ┌────────▼──────────┐
                          │  provena-web  │  │   provena-api     │
                          │  Next.js 14   │  │   Django 5.1      │
                          │  (Vercel /    │  │   DRF             │
                          │   Render)     │  │   (Render)        │
                          └───────────────┘  └──────┬────────────┘
                                                    │
                    ┌───────────────────────────────┼──────────────────────────┐
                    │                               │                          │
          ┌─────────▼──────┐            ┌───────────▼────┐        ┌───────────▼──────┐
          │  PostgreSQL 16  │            │   Redis 7       │        │  Celery Worker   │
          │  (primary DB)   │            │  (cache/queue)  │        │  + Celery Beat   │
          └────────────────┘            └────────────────┘        └──────────────────┘
                                                                            │
                    ┌───────────────────────────────────────────────────────┤
                    │                       │                               │
          ┌─────────▼──────┐    ┌───────────▼────┐              ┌──────────▼────────┐
          │   Stripe API    │    │  S3 / R2        │              │  SendGrid / SES   │
          │  (payments +    │    │  (file storage) │              │  (transactional   │
          │   Connect)      │    │                 │              │   email)          │
          └────────────────┘    └────────────────┘              └───────────────────┘
```

---

## 3. Django Application Structure

```
provena-api/
├── apps/
│   ├── accounts/          # User model, auth, roles, 2FA
│   ├── catalogue/         # Categories, products, variants, images
│   ├── disputes/          # Dispute lifecycle, events, admin resolution, refund tracking
│   ├── inventory/         # Stock levels, lots, audit log
│   ├── marketplace/       # Cart, wishlist, reviews, homepage curation
│   ├── notifications/     # In-app and email notification delivery
│   ├── orders/            # Order lifecycle, sub-orders
│   ├── payments/          # Stripe integration, payouts, refunds
│   ├── suppliers/         # Supplier profile, KYC, Stripe Connect onboarding
│   └── analytics/         # Reports, aggregated metrics
├── config/
│   ├── settings/
│   │   ├── base.py        # Common settings
│   │   ├── development.py # DEBUG=True, console email, local storage
│   │   └── production.py  # Security headers, S3, SendGrid, Sentry
│   ├── urls.py            # Root URL routing
│   └── celery.py          # Celery app configuration
└── manage.py
```

### Per-App Structure

Each app follows the same internal layout:

```
apps/{domain}/
├── __init__.py
├── admin.py       # Django admin registration
├── apps.py        # AppConfig
├── models.py      # Database models
├── serializers.py # DRF serialisers
├── views.py       # DRF ViewSets / APIViews
├── urls.py        # URL patterns for this domain
├── permissions.py # Custom DRF permission classes
├── services.py    # Business logic (no direct model imports from other domains)
├── tasks.py       # Celery tasks
└── tests/
    ├── test_models.py
    ├── test_serializers.py
    ├── test_views.py
    └── test_services.py
```

The critical rule: **`services.py` is the only file that may import from another app's `services.py`**. Models are never imported across app boundaries in application code. This preserves the ability to extract apps as services.

---

## 4. Request Lifecycle

### 4.1 Public Product Browse

```
Browser
  -> Cloudflare (cache hit: served from edge, <10ms)
  -> Next.js SSR (cache miss: renders page server-side)
       -> GET /api/v1/catalogue/products/?category=fruit
            -> Nginx
            -> Gunicorn worker
            -> Django view
            -> Redis cache check (5-minute TTL)
            -> PostgreSQL query (if cache miss)
            -> DRF serialiser
            -> JSON response
  -> Next.js returns HTML with embedded data
  -> Browser hydrates React
```

### 4.2 Checkout and Payment

```
Buyer clicks Pay
  -> Next.js -> POST /api/v1/payments/checkout/
  -> Django creates Order (status=PENDING_PAYMENT)
  -> Django calls Stripe: creates PaymentIntent or Checkout Session
  -> Returns {client_secret} or {checkout_url} to frontend
  -> Frontend: Stripe Elements handles card input (card data never hits Django)
  -> Stripe processes payment
  -> Stripe POSTs webhook to /api/v1/payments/webhook/
  -> Django verifies webhook signature
  -> Django: Order status -> CONFIRMED
  -> Celery: send_order_confirmation (email to buyer + supplier)
  -> Celery: reserve_stock (decrement available quantity)
  -> Celery: trigger_payout (after delivery confirmed)
```

### 4.3 Background Job Execution

```
Celery Beat (scheduler)
  -> Enqueues task message to Redis
  -> Celery Worker picks up task
  -> Executes task (DB query, external API call, email send)
  -> Records result in django-celery-results (Postgres)
  -> Sentry captures any exceptions
```

---

## 5. Frontend Architecture

```
provena-web/
├── src/
│   ├── app/                   # Next.js App Router pages
│   │   ├── (marketing)/       # Public: home, about, contact
│   │   ├── (marketplace)/     # Products, categories, product detail
│   │   ├── (checkout)/        # Cart, checkout, order confirmation
│   │   ├── (auth)/            # Login, register, forgot password
│   │   ├── (buyer)/           # Order history, profile, wishlist
│   │   ├── (supplier)/        # Product management, orders, analytics
│   │   └── (admin)/           # Platform admin dashboard
│   ├── components/
│   │   ├── ui/                # shadcn/ui primitives
│   │   ├── layout/            # Header, footer, nav, sidebar
│   │   ├── catalogue/         # ProductCard, ProductGrid, FilterPanel
│   │   ├── checkout/          # CartDrawer, CheckoutForm, StripeWrapper
│   │   └── shared/            # Notification bell, Avatar, LoadingSpinner
│   ├── lib/
│   │   ├── api/               # Axios client + typed API functions
│   │   ├── auth/              # JWT storage, token refresh, guards
│   │   └── utils/             # formatPrice, formatDate, cn()
│   └── types/
│       └── index.ts           # Shared TypeScript interfaces
```

Route groups (parentheses) are used so that layouts can be shared within a group without affecting the URL.

---

## 6. Domain Interaction Map

```
accounts ◄──────── all domains (every model has a user/actor FK)
    │
    ▼
suppliers ◄──── catalogue
                    │
                    ▼
                inventory ◄─── orders ◄─── payments
                                │               │
                                ▼               ▼
                           marketplace       disputes
                                │               │
                                └───────┬───────┘
                                        ▼
                          notifications ◄─── all domains (trigger points)
                                │
                                ▼
                           analytics (reads from all; writes to none)
```

Key rules:
- `analytics` is read-only aggregate; never writes to other domains
- `notifications` is write-only from other domains' perspective; tasks call `notifications.services.send()`
- `payments` talks to `orders` to update status; never to `catalogue` or `inventory` directly

---

## 7. Deployment Architecture (Production)

```
                Internet
                   │
          ┌────────▼────────┐
          │   Cloudflare    │
          │ (DNS, WAF, CDN) │
          └────────┬────────┘
                   │
     ┌─────────────┴─────────────┐
     │                           │
┌────▼───────┐           ┌───────▼───────────┐
│  Vercel    │           │  Render            │
│  (Next.js) │           │  Web Service       │
│            │           │  (Django + Nginx)  │
└────────────┘           └───────┬────────────┘
                                 │
                ┌────────────────┼─────────────────┐
                │                │                 │
        ┌───────▼──────┐ ┌───────▼──────┐ ┌───────▼──────┐
        │ Render Postgres│ │ Render Redis │ │ Render Worker│
        │  (managed DB)  │ │  (cache)     │ │  (Celery)    │
        └───────────────┘ └─────────────┘ └──────────────┘
```

All traffic enters via Cloudflare. HTTPS enforced at the edge. API and frontend deployed on Render initially; migrating to AWS or GCP when monthly revenue justifies the operational overhead.

---

## 8. Architecture Decision Records

Significant decisions are recorded in `docs/DECISIONS.md`. The ADR format is:

```
## ADR-NNN: Title
**Date:** YYYY-MM-DD
**Status:** Accepted | Superseded by ADR-NNN
**Context:** Why this decision was needed
**Decision:** What was decided
**Consequences:** What this means for future work
```

See `DECISIONS.md` for all current ADRs.
