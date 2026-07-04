# provena-web

Next.js frontend for the Provena multi-supplier marketplace platform.

This directory is part of the [Provena monorepo](../README.md). All operational documentation (setup, deployment, contributing) lives in [`docs/`](../docs/).

## Quick Links

| Document | Description |
|---|---|
| [Developer Onboarding](../docs/onboarding.md) | Local setup, running tests, first change |
| [Production Deployment](../docs/deployment.md) | Docker Compose, environment variables, Vercel |
| [Contributing](../docs/contributing.md) | Branching, code standards, PR checklist |

## Project Structure

```
src/
├── app/
│   ├── (auth)/          # Login
│   ├── (checkout)/      # Cart and Stripe checkout
│   ├── account/         # Buyer payments, notifications, 2FA security
│   ├── admin/           # Platform admin (suppliers, orders, analytics, banners, audit)
│   ├── catalogue/       # Product listing (SSR) and detail (SSR + ISR)
│   ├── orders/          # Order detail
│   ├── supplier/        # Supplier dashboard, products, inventory, payouts
│   └── page.tsx         # Homepage
├── components/
│   ├── admin/           # Admin shell, admin-specific components
│   ├── catalogue/       # ProductCard, ProductGrid, FilterPanel
│   ├── checkout/        # CartDrawer, CheckoutForm, StripeWrapper
│   ├── supplier/        # Supplier shell, supplier-specific components
│   ├── ui/              # Shared primitives
│   └── layout/          # Header, footer, navigation
├── lib/
│   ├── api/             # Axios client and typed API functions per domain
│   ├── auth/            # Token management
│   └── utils/           # formatPrice, formatDate, cn()
├── store/
│   ├── auth.ts          # Zustand auth store (login, logout, setUser, TOTP cookies)
│   └── cart.ts          # Zustand cart store
└── middleware.ts         # Route protection by role and TOTP enrolment
```

## Scripts

```bash
npm run dev          # Development server with HMR
npm run build        # Production build
npm start            # Production server
npm run lint         # ESLint (zero warnings)
npm run type-check   # TypeScript check
npm run test:unit    # Vitest unit tests
npm run test:e2e     # Playwright E2E tests (requires running API)
```

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_SENTRY_DSN=          # optional
```

See `.env.example` for the full list. Copy to `.env.local` for local development.

## Rendering Strategy

| Route | Strategy | Notes |
|---|---|---|
| `/catalogue/` | SSR + ISR (60s) | SEO-sensitive; revalidates every minute |
| `/catalogue/[slug]/` | SSR + ISR + `generateStaticParams` | Pre-rendered for top products; dynamic fallback |
| `/admin/*`, `/supplier/*` | CSR | Auth-gated; no SEO requirement |
| `/` | SSR | Homepage fetches active banners and featured products server-side |
