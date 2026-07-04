# provena-web

Next.js 14 frontend for the Provena supply chain and marketplace platform.

## Prerequisites

- Node.js 20+
- The `provena-api` running at `http://localhost:8000`

## Getting started

```bash
# Install dependencies
npm install

# Copy environment config
cp .env.example .env.local
# Edit .env.local with your Stripe publishable key

# Start development server
npm run dev
```

Frontend available at `http://localhost:3000`.

## Bootstrapping

This project should be initialised with:

```bash
npx create-next-app@latest provena-web \
  --typescript \
  --tailwind \
  --app \
  --src-dir \
  --import-alias "@/*"
```

Then add:

```bash
npm install @tanstack/react-query zustand react-hook-form zod axios @stripe/stripe-js @stripe/react-stripe-js
npm install -D @types/node vitest @testing-library/react @testing-library/user-event @playwright/test
npx shadcn@latest init
```

## Project structure

```
src/
├── app/
│   ├── (marketing)/     # Home, about, contact
│   ├── (marketplace)/   # Products, catalogue, search
│   ├── (checkout)/      # Cart, checkout, confirmation
│   ├── (auth)/          # Login, register, password reset
│   ├── (buyer)/         # Order history, profile, wishlist
│   ├── (supplier)/      # Product management, orders, payouts
│   └── (admin)/         # Platform admin dashboard
├── components/
│   ├── ui/              # shadcn/ui primitives
│   ├── layout/          # Header, footer, navigation
│   ├── catalogue/       # ProductCard, ProductGrid, FilterPanel
│   ├── checkout/        # CartDrawer, CheckoutForm, StripeWrapper
│   └── shared/          # NotificationBell, Avatar, LoadingSpinner
├── lib/
│   ├── api/             # Axios client and typed API functions
│   ├── auth/            # Token management and route guards
│   └── utils/           # formatPrice, formatDate, cn()
└── types/
    └── index.ts         # Shared TypeScript interfaces
```

## Documentation

See `provena-api/docs/` for BRD, TRD, Architecture, and Compliance documents.
