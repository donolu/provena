# provena-api

Django REST Framework API for the Provena multi-supplier marketplace platform.

This directory is part of the [Provena monorepo](../README.md). All operational documentation (setup, deployment, contributing) lives in [`docs/`](../docs/).

## Quick Links

| Document | Description |
|---|---|
| [Developer Onboarding](../docs/onboarding.md) | Local setup, running tests, first change |
| [Production Deployment](../docs/deployment.md) | Docker Compose, environment variables, Render/Vercel |
| [Contributing](../docs/contributing.md) | Branching, code standards, PR checklist |
| [BRD](docs/BRD.md) | Business requirements: features, user stories, success metrics |
| [TRD](docs/TRD.md) | Technical requirements: stack, API design, data architecture |
| [Architecture](docs/ARCHITECTURE.md) | System design, component diagram, domain structure |
| [Compliance](docs/COMPLIANCE.md) | PCI DSS, UK GDPR, OWASP Top 10, accessibility |
| [Decisions](docs/DECISIONS.md) | Architecture decision records (ADR-001 through ADR-007) |

## Project Structure

```
apps/
├── accounts/      # Auth, users, roles, TOTP 2FA, rate limiting, audit log
├── catalogue/     # Categories, products, variants, images, banners
├── inventory/     # Stock levels, lots, expiry tracking, movement log
├── marketplace/   # Cart, wishlist, reviews
├── notifications/ # In-app and transactional email notifications
├── orders/        # Order lifecycle, disputes, returns
├── payments/      # Stripe integration, supplier payouts, refunds
├── suppliers/     # Vendor onboarding, KYC document review
└── analytics/     # Read-only reports and dashboards
config/
├── settings/
│   ├── base.py         # Shared settings
│   ├── development.py  # Local development
│   └── production.py   # Production (security headers, S3, Sentry)
├── celery.py
└── urls.py
```

## API

- Base URL: `/api/v1/`
- Authentication: JWT (access token 15 min, refresh token 30 days with rotation)
- OpenAPI schema: `/api/schema/swagger-ui/`
- All responses follow DRF's standard format; errors include a `detail` or field-level key

## Running Tests

```bash
# From this directory, with the venv active
pytest

# With coverage report
pytest --cov=apps --cov-report=term-missing
```

Minimum 80% coverage required. CI fails below this threshold.
