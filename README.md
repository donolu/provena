# Provena

Provena is a multi-supplier marketplace platform for the UK market. It connects buyers with vetted suppliers across product categories, handling the full commercial lifecycle: discovery, ordering, payment, inventory, fulfilment, and post-sale support. The platform is UK GDPR compliant and designed to PCI DSS SAQ-A scope.

## Actors

| Actor | Description |
|---|---|
| **Buyer** | Registered consumer. Browses the catalogue, adds items to cart, pays via Stripe, tracks orders, raises disputes and returns, writes reviews. |
| **Supplier** | Vetted vendor. Lists products and variants, manages stock (lot intake, adjustments, expiry tracking), receives orders, dispatches sub-orders, receives Stripe Connect payouts. |
| **Admin** | Platform operator. Approves and suspends suppliers, moderates reviews and disputes, manages homepage banners, sets per-supplier commission rates, exports financial reports, views the full audit log. |
| **System** | Celery beat and worker processes. Releases expired cart reservations, sends low-stock and lot-expiry alerts, triggers payouts on delivery, sends transactional emails. |

## Key Features

**Marketplace**
- Product catalogue with categories, variants, images, and supplier ratings
- Full-text search (PostgreSQL; Typesense/Elasticsearch on the roadmap)
- Wishlist, cart with stock reservation, and guest checkout
- Homepage banners managed by admin

**Ordering and Payments**
- Multi-supplier orders: one checkout creates one `Order` containing one `SubOrder` per supplier
- Stripe Elements for card capture; Stripe Checkout Session as fallback
- Stripe Connect for supplier payouts (platform deducts commission on delivery)
- Configurable per-supplier commission rate; default 10%
- Buyers: full payment history at `/account/payments`
- Suppliers: payout ledger at `/supplier/payouts`

**Inventory**
- Per-variant stock levels with reservation tracking
- Lot intake with expiry dates; daily alerts for expiring lots
- Stock movement audit log

**Supplier Onboarding**
- Self-service registration with KYC document upload (S3/Cloudflare R2)
- Admin review workflow: pending → approved/rejected/suspended
- 2FA (TOTP) mandatory before supplier routes are accessible

**Administration**
- Analytics dashboard: revenue trends, top products, supplier performance, inventory health
- CSV financial report export
- Admin action audit log (`@audit_action` decorator, queryable via API)
- User management: suspend, activate, view roles

**Notifications**
- In-app notification feed
- Transactional emails: order confirmation, delivery confirmation
- Per-user notification preferences

**Security**
- JWT authentication with 15-minute access tokens and 30-day rotating refresh tokens
- TOTP 2FA mandatory for Supplier and Admin roles
- Account lockout after 5 failed attempts
- Role-based rate limiting: Anon 100/hr, Buyer 1,000/hr, Supplier 2,000/hr, Admin exempt
- Weekly OWASP ZAP DAST scan; Bandit + Safety on every push
- PCI DSS SAQ-A (Stripe handles all card data)
- UK GDPR controls: consent, retention schedules, data subject rights

## Technology Stack

| Layer | Technology |
|---|---|
| API | Django 5.1 + Django REST Framework 3.15 |
| Task queue | Celery 5.4 + Redis 7 |
| Database | PostgreSQL 16 |
| Frontend | Next.js 16 (App Router, SSR + ISR) |
| Payments | Stripe API + Stripe Connect |
| Storage | AWS S3 / Cloudflare R2 |
| Email | SendGrid / AWS SES / Resend |
| Error tracking | Sentry (backend + frontend) |
| Reverse proxy | Nginx 1.27 |
| Container runtime | Docker + Docker Compose |

## Repository Structure

```
provena/
├── provena-api/          Django REST API
│   ├── apps/             Eight domain apps (accounts, catalogue, inventory, …)
│   ├── config/           Settings (base, development, production), Celery, URLs
│   ├── docs/             BRD, TRD, Architecture, Compliance, ADRs
│   └── Dockerfile
├── provena-web/          Next.js frontend
│   ├── src/app/          39 routes across buyer, supplier, admin, checkout
│   ├── src/components/   UI, layout, domain components
│   ├── src/lib/          Axios API client, auth, utilities
│   └── Dockerfile
├── nginx/
│   └── nginx.conf        Reverse proxy (routes /api/ to Django, / to Next.js)
├── docs/                 Cross-cutting operational docs
│   ├── onboarding.md     Local development setup
│   ├── deployment.md     Production deployment guide
│   ├── contributing.md   Development workflow and standards
│   └── backlog.md        Roadmap and known limitations
├── load-tests/
│   └── locustfile.py     Locust load test scenarios
├── .github/
│   └── workflows/
│       ├── api.yml       Django CI (lint, type-check, pytest)
│       ├── web.yml       Next.js CI (ESLint, type-check, Vitest)
│       └── security-scan.yml  Weekly OWASP ZAP DAST
├── docker-compose.yml    Production stack
├── docker-compose.dev.yml  Development overrides
├── .pre-commit-config.yaml  Git hooks (ruff, bandit)
└── GAPS.md               Completed work log and deferred items
```

## Quick Start

The fastest way to run the full stack locally is with Docker Compose:

```bash
git clone https://github.com/donolu/provena.git
cd provena

# Copy and configure environment files
cp provena-api/.env.example provena-api/.env
cp provena-web/.env.example provena-web/.env.local
# Edit both files — minimum: add your Stripe test keys

# Start all services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# In a separate terminal: apply migrations and create a superuser
docker compose exec api python manage.py migrate
docker compose exec api python manage.py createsuperuser
```

- API: `http://localhost:8000/api/v1/`
- Django admin: `http://localhost:8000/admin/`
- Frontend: `http://localhost:3000`
- API docs (OpenAPI): `http://localhost:8000/api/schema/swagger-ui/`

For a full setup guide without Docker, see [docs/onboarding.md](docs/onboarding.md).

## Documentation Index

| Document | Location | Description |
|---|---|---|
| Developer Onboarding | [docs/onboarding.md](docs/onboarding.md) | Local setup, prerequisites, running tests |
| Production Deployment | [docs/deployment.md](docs/deployment.md) | Docker Compose, environment variables, external services |
| Contributing | [docs/contributing.md](docs/contributing.md) | Branching, standards, PR process, adding endpoints/pages |
| Backlog and Roadmap | [docs/backlog.md](docs/backlog.md) | Not yet implemented, known limitations, roadmap |
| Business Requirements | [provena-api/docs/BRD.md](provena-api/docs/BRD.md) | Features, user stories, success metrics |
| Technical Requirements | [provena-api/docs/TRD.md](provena-api/docs/TRD.md) | Stack, API design, data architecture |
| System Architecture | [provena-api/docs/ARCHITECTURE.md](provena-api/docs/ARCHITECTURE.md) | Component diagram, domain structure, request lifecycle |
| Compliance | [provena-api/docs/COMPLIANCE.md](provena-api/docs/COMPLIANCE.md) | PCI DSS, UK GDPR, OWASP Top 10, WCAG 2.1 |
| Architecture Decisions | [provena-api/docs/DECISIONS.md](provena-api/docs/DECISIONS.md) | ADR-001 through ADR-007 |
