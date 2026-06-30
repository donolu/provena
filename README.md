# provena-api

Django REST Framework API for the Provena supply chain and marketplace platform.

## Documentation

| Document | Description |
|---|---|
| [BRD](docs/BRD.md) | Business requirements: features, user stories, success metrics |
| [TRD](docs/TRD.md) | Technical requirements: stack, API design, data architecture |
| [Architecture](docs/ARCHITECTURE.md) | System design, component diagram, domain structure |
| [Compliance](docs/COMPLIANCE.md) | PCI DSS, UK GDPR, OWASP Top 10, accessibility |
| [Decisions](docs/DECISIONS.md) | Architecture decision records |

## Prerequisites

- Docker and Docker Compose
- Python 3.12 (for local development without Docker)

## Getting started

```bash
# Clone the repo
git clone https://github.com/donolu/provena-api.git
cd provena-api

# Copy environment config
cp .env.example .env
# Edit .env and add your Stripe test keys

# Start all services
docker compose up

# In a second terminal, run migrations
docker compose exec api python manage.py migrate

# Create an admin user
docker compose exec api python manage.py createsuperuser
```

API available at `http://localhost:8000/api/v1/`  
Admin panel at `http://localhost:8000/admin/`

## Development

```bash
# Install dependencies locally
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
ruff check .
ruff format .

# Type check
mypy apps/

# Security scan
bandit -r apps/
safety check
```

## Project structure

```
apps/
├── accounts/      # Auth, users, roles, 2FA
├── catalogue/     # Categories, products, variants, images
├── inventory/     # Stock levels, lots, audit log
├── marketplace/   # Cart, wishlist, reviews
├── notifications/ # In-app and email notifications
├── orders/        # Order lifecycle, disputes
├── payments/      # Stripe integration, payouts, refunds
├── suppliers/     # Vendor onboarding, KYC, performance
└── analytics/     # Reports and dashboards
config/
├── settings/
│   ├── base.py         # Shared settings
│   ├── development.py  # Local development
│   └── production.py   # Production (security headers, S3, Sentry)
├── celery.py
└── urls.py
```

## Environment variables

See `.env.example` for the full list with descriptions.

## Deployment

See `docs/TRD.md` (Infrastructure section) for deployment instructions for Render (initial) and AWS (scaled).
