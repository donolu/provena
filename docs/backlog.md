# Backlog, Known Limitations, and Roadmap

This document tracks everything not yet built or not yet working correctly. Items are grouped by category and roughly prioritised. The GAPS.md file at the repo root serves as the completed-work log; this file tracks what remains.

---

## Not Yet Implemented

### Search (MKT-09)

**Current state:** The catalogue page filters products in-memory via PostgreSQL `ILIKE` queries. Full-text search works for simple queries but is slow on large catalogues and does not support ranking, typo-tolerance, or faceted filtering.

**Target state:** Typesense (preferred for self-hosting simplicity) or Algolia. Products indexed on save via a Celery task; search queries hit the search engine, not Postgres.

**Blocker:** None; requires a Typesense instance and a one-time sync task.

---

### SMS and WhatsApp Notifications (NOT-04)

**Current state:** In-app notifications and transactional emails only.

**Target state:** Twilio for SMS (order status updates, delivery confirmation). WhatsApp Business API via Twilio for high-value buyers. Opt-in at account level.

**Blocker:** Twilio account, per-country A2P 10DLC registration (US), and compliance review for WhatsApp Business.

**Note:** Marked optional in the BRD. Not required for launch.

---

### Related Products (MKT-07)

**Current state:** Product detail page has no related products section.

**Target state:** "You might also like" grid based on the same category and supplier. Simple SQL implementation; ML-based collaborative filtering is a future phase.

**Effort:** Small (backend query + frontend section).

---

### Recently Viewed Products (MKT-08)

**Current state:** Not tracked.

**Target state:** Client-side tracking in Zustand, persisted to `localStorage`. Show a "Recently viewed" strip on the homepage and product detail page.

**Effort:** Frontend-only; no backend changes.

---

### Personalised Homepage Recommendations (ANA-04)

**Current state:** Homepage shows admin-curated banners and the most recently added featured products.

**Target state:** Per-user recommendations based on order history and browsing behaviour. Requires a recommendation engine (collaborative or content-based filtering) or an ML-as-a-service provider (AWS Personalise, Recombee).

**Effort:** High; requires purchase history data at meaningful volume first.

---

### Guest Checkout

**Current state:** Adding to cart requires a registered account.

**Target state:** Anonymous cart (session-based) with account creation prompted at checkout. Post-checkout, the order is linked to the newly created account or stored against the email address.

**Effort:** Moderate; requires changes to the cart model, middleware, and checkout flow.

---

### Product Reviews — Verified Purchase Gate

**Current state:** Any authenticated buyer can submit a review for any product.

**Target state:** Reviews restricted to buyers who have a confirmed order containing that product variant.

**Effort:** Small; add an `OrderItem` existence check in `ReviewCreateView`.

---

### Supplier Storefront Pages

**Current state:** Products list the supplier name but there is no dedicated supplier profile page.

**Target state:** `/suppliers/<slug>/` showing the supplier's name, logo, description, average rating, and product grid.

**Effort:** Small; backend endpoint exists; frontend page needed.

---

### Buyer Address Book

**Current state:** Delivery address is entered at checkout but not saved for reuse.

**Target state:** Saved addresses in the buyer account; default address pre-filled at checkout.

**Effort:** Moderate; new `BuyerAddress` model and checkout UI changes.

---

### Product Variant Images

**Current state:** Product images are at the product level. All variants share the same image set.

**Target state:** Per-variant images (e.g. different colours show different photos). Requires a `VariantImage` model linked to `ProductVariant`.

**Effort:** Small to moderate.

---

### Admin: Bulk Product Actions

**Current state:** Products are featured/unfeatured one at a time.

**Target state:** Multi-select in the admin products table for bulk feature toggle, bulk category assignment, bulk status change.

**Effort:** Frontend-only change; API supports `PATCH /admin/products/<id>/` already.

---

## Infrastructure Gaps

### PgBouncer (Connection Pooling)

**Current state:** Django connects directly to PostgreSQL. At higher concurrency, this will exhaust the Postgres `max_connections` limit.

**Target state:** PgBouncer in transaction pooling mode as a sidecar in `docker-compose.yml`. Render Managed Postgres includes PgBouncer; for self-hosted, add the `edoburu/pgbouncer` image.

**Impact:** Required before scaling beyond ~50 concurrent API workers.

---

### Prometheus Metrics Endpoint

**Current state:** No application-level metrics are exposed. Sentry captures errors and traces, but infrastructure metrics (request counts, queue depth, task latency) are not available for alerting.

**Target state:** `django-prometheus` exposing `/metrics` for Prometheus scraping; Grafana dashboards for request rate, error rate, Celery queue depth, and database connection pool usage.

**Effort:** Small to add the endpoint; moderate to build Grafana dashboards.

---

### Staging Environment

**Current state:** There is no staging environment. All testing happens locally or against production.

**Target state:** A staging deployment on Render (or a Docker Compose stack on a second VPS) with test Stripe keys and a separate database. Deployed automatically on merge to `main` before a manual gate to production.

**Effort:** Infrastructure configuration; no code changes.

---

### Zero-Downtime Deployments

**Current state:** Docker Compose deployments have a brief (~5-15 second) restart window where the API is unavailable.

**Target state:** Rolling updates via a load balancer (two API containers, health-check-gated rollover) or deployment to ECS Fargate (which supports rolling updates natively).

**Effort:** Requires a load balancer (Nginx upstream with two backends) or migration to ECS.

---

### Database Backups to S3

**Current state:** Render managed Postgres takes daily snapshots. Self-hosted deployments have no automated backup.

**Target state:** A Celery beat task that runs `pg_dump`, gzips the output, and uploads to S3 or R2 with a 30-day retention lifecycle rule.

**Effort:** Small.

---

## Technical Debt

### OpenAPI Client Generation

**Current state:** Frontend TypeScript types (`src/lib/api/types.ts`) are maintained manually. Any API model change must be manually reflected in the frontend types.

**Target state:** `openapi-typescript-codegen` (or `openapi-ts`) auto-generates types and API functions from the `drf-spectacular` schema on every API CI run. The generated output is committed to the frontend directory.

**Effort:** Small; one-time setup.

---

### Stripe Connect Onboarding Flow

**Current state:** Supplier `stripe_account_id` must be set manually by an admin. There is no in-app Stripe Connect onboarding for suppliers.

**Target state:** Supplier clicks "Connect Stripe" in their dashboard; this initiates a Stripe Connect OAuth flow returning to `/supplier/payouts/?connected=1`. The `stripe_account_id` is saved automatically.

**Effort:** Moderate; Stripe Connect OAuth is well-documented.

---

### Test Coverage: Notifications and Analytics Apps

**Current state:** The `notifications` and `analytics` apps have lower test coverage than the 80% floor. CI passes because the floor is applied across the project, not per-app.

**Target state:** Per-app coverage floor at 80% (`--cov-fail-under=80` applied at app level in CI matrix).

---

### E2E Tests Depend on Live API

**Current state:** Playwright E2E tests in `provena-web/e2e/` are skipped unless `TEST_USER_EMAIL` and `TEST_USER_PASSWORD` are set in the environment. They require a running backend at `localhost:8000`, which is not available in the standard web CI job.

**Target state:** A dedicated E2E CI job (`e2e.yml`) that spins up the full Docker Compose stack, runs Playwright, and tears down. This should run on PRs to `main` only (not on every push).

**Effort:** Moderate CI work; test code itself is ready.

---

### Inventory: Race Condition on Simultaneous Stock Reservation

**Current state:** `reserve_stock` in the marketplace app uses `select_for_update()` to lock the `StockLevel` row. Under very high concurrency, the queue of waiting transactions can cause timeout errors visible to the buyer.

**Target state:** Evaluate a Redis-based optimistic lock for reservations, decoupling the cart reservation from a Postgres row lock. This is a performance concern, not a correctness concern (the current implementation does not oversell).

---

### Product Image Optimisation

**Current state:** Product images are stored at original resolution. The frontend uses `<img>` tags (not `next/image`) because image domains are dynamic (S3 bucket URL not known at build time).

**Target state:** Configure `next.config.mjs` `images.remotePatterns` with the known S3/R2 bucket hostname, then migrate to `next/image` for automatic WebP conversion and responsive sizing.

---

## Won't Fix (Accepted Limitations)

| Item | Reason |
|---|---|
| SMS 2FA | WhatsApp/SMS 2FA (NOT-04) is optional per BRD. TOTP app 2FA covers the requirement for privileged roles. |
| Multi-currency | All prices stored in GBP pence (integer). Stripe supports multi-currency but the platform is UK-market only at launch. |
| Mobile apps | Not in scope. The Next.js frontend is responsive and serves as the mobile experience. |
| Real-time order tracking (websocket) | Nginx config includes WebSocket upgrade headers for HMR; application-level WebSocket push (for live order tracking) is not implemented. Polling on the order detail page is the current behaviour. |
| GDPR data portability export | The right to data portability (Article 20) is acknowledged in COMPLIANCE.md. A self-service export endpoint is not yet built; it currently requires an admin to run a manual extract. |
