# Provena - Known gaps and outstanding work

Last updated: 2026-07-04

---

## Priority 1 - Revenue-critical (fix before launch)

### 1a. Celery tasks - payout not triggered on delivery
**File:** `provena-api/apps/orders/services.py` `deliver_sub_order()`
**Gap:** When a sub-order is marked DELIVERED, no payout is triggered. The `process_payout` service and Stripe Connect transfer logic are complete but never called automatically.
**Fix:** Add `trigger_payout` Celery task in `apps/payments/tasks.py`; call it from `deliver_sub_order()`.
**Status:** FIXED (2026-07-04)

### 1b. Celery tasks - lot expiry alerts missing
**File:** `provena-api/apps/inventory/tasks.py`
**Gap:** `check_lot_expiry` task is an empty stub. `StockLot.expires_at` exists but is never checked. Suppliers never receive expiry warnings (INV-06).
**Fix:** Implement task; query lots expiring within N days (configurable, default 3); send in-app notification per supplier.
**Scheduled:** Daily via `CELERY_BEAT_SCHEDULE`.
**Status:** FIXED (2026-07-04)

### 1c. Celery beat schedule incomplete
**File:** `provena-api/config/settings/base.py` `CELERY_BEAT_SCHEDULE`
**Gap:** Only `release-expired-cart-reservations` is scheduled. `check_low_stock_levels` and `check_lot_expiry` tasks exist but are not scheduled.
**Status:** FIXED (2026-07-04)

---

## Priority 2 - Significant UX gaps

### 2a. Supplier inventory management UI missing
**Files:** No `/supplier/inventory` page exists.
**Gap:** Suppliers cannot view stock levels, receive stock (lot intake), adjust quantities, or see movement history from the portal. Backend has full inventory views (`InventoryListView`, `ReceiveStockView`, `AdjustStockView`, `StockLotListView`, `StockMovementListView`).
**Fix:** Create `/supplier/inventory/page.tsx` with:
  - Stock level table per variant (quantity, reserved, available, low-stock indicator)
  - "Receive stock" modal (lot number, quantity, expiry date)
  - Manual adjustment modal (delta + reason)
  - Stock movements tab
**Status:** FIXED (2026-07-04)

### 2b. Buyer payment history missing (PAY-07)
**Gap:** Buyers have order history but no receipt/payment page. `Payment` model and backend views exist.
**Fix:** Added `getPayments()` to `lib/api/orders.ts`; created `/account/payments/page.tsx`; added "Payment history" link to account dropdown in nav.
**Status:** FIXED (2026-07-04)

### 2c. Supplier ratings not surfaced (MKT-06)
**Gap:** Reviews exist on product detail pages but no aggregated supplier rating is shown on product listings or supplier profiles. `Review` model has `rating` field.
**Fix:** Added `average_rating` and `review_count` `SerializerMethodField`s to `ProductSerializer`; star display added to `ProductCard`.
**Status:** FIXED (2026-07-04)

### 2d. Transactional emails not fully wired (NOT-01)
**Gap:** `deliver_sub_order` did not send a delivery confirmation email to the buyer.
**Fix:** Added `send_delivery_confirmation()` to `apps/notifications/email_service.py`; called from `deliver_sub_order()` in `apps/orders/services.py` with try/except guard.
**Status:** FIXED (2026-07-04)

---

## Priority 3 - Admin and operational gaps

### 3a. Commission rate management UI missing (ADM-06)
**Gap:** Commission rates can only be changed via Django admin. No frontend UI.
**Fix:** `CommissionCell` inline-edit component already exists in `/admin/suppliers/page.tsx`; calls `updateSupplierCommission`. Pre-existing, not a gap.
**Status:** FIXED (pre-existing)

### 3b. CSV financial reports missing (ADM-07)
**Gap:** No export endpoint. Analytics views return JSON only.
**Fix:** Added `GET /analytics/export/csv/?from=&to=` endpoint with `StreamingHttpResponse`; "Export CSV" button on admin analytics page.
**Status:** FIXED (2026-07-04)

### 3c. Admin audit log missing (ADM-08)
**Gap:** Admin actions (suspend user, approve supplier, process refund, etc.) are not logged to a queryable audit trail.
**Fix:** `AuditLog` model in `apps/accounts`; `@audit_action` decorator applied to 6 admin views (supplier approve/suspend/reject, user suspend/activate, payment refund); `GET /auth/admin/audit-log/` paginated endpoint; admin UI at `/admin/audit-log` with action filter and pagination.
**Status:** FIXED (2026-07-04)

### 3d. Homepage content management missing (ADM-05)
**Gap:** No banner or featured-category management. Admin can toggle `is_featured` on products but cannot manage homepage banners or announcement text.
**Fix:** `Banner` model in `apps/catalogue`; migration `0002_add_banner_model`; `BannerSerializer`/`BannerWriteSerializer`; `BannerListView` (public), `AdminBannerListCreateView`, `AdminBannerDetailView`; admin UI at `/admin/banners` with inline toggle/edit/delete; banners rendered on storefront homepage between hero and featured products.
**Status:** FIXED (2026-07-04)

---

## Priority 4 - Non-functional and infrastructure

### 4a. Rate limiting - supplier and admin tiers missing (TRD §3.4)
**File:** `provena-api/config/settings/base.py`
**Gap:** Only `anon` (100/hr) and `user` (1000/hr) throttle rates. TRD requires Supplier (2000/hr) and Admin (no limit).
**Fix:** Created `apps/accounts/throttling.py` with `BuyerRateThrottle` (1000/hr), `SupplierRateThrottle` (2000/hr), `AdminRateThrottle` (exempt). Each class only applies to its role, avoiding double-throttling. Wired into `DEFAULT_THROTTLE_CLASSES`.
**Status:** FIXED (2026-07-04)

### 4b. Catalogue pages are client-side rendered (TRD §1)
**Gap:** TRD specifies SSR for SEO-sensitive pages (catalogue, product detail). Both are currently `'use client'` pages with no static generation.
**Fix:** Server component wrappers for both pages: `catalogue/page.tsx` and `catalogue/[slug]/page.tsx` fetch with `revalidate = 60`; pass `initialData` to client components; `generateStaticParams` and `generateMetadata` on product detail; `withSentryConfig` wraps `next.config.mjs`.
**Status:** FIXED (2026-07-04)

### 4c. Sentry not wired
**Gap:** `SENTRY_DSN` env var exists in TRD but `sentry-sdk` is not initialised in `settings/production.py` or frontend `_app`.
**Fix:** Backend: `sentry-sdk[django]` already in `pyproject.toml`; `sentry_sdk.init()` already in `settings/production.py`. Frontend: installed `@sentry/nextjs`; created `sentry.client.config.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`; wired `withSentryConfig` in `next.config.mjs`; `global-error.tsx` captures unhandled errors.
**Status:** FIXED (2026-07-04)

---

## Testing gaps (TRD §7)

### T1. OWASP ZAP DAST - not in CI
**Gap:** No dynamic security scan runs against the API.
**Fix:** `.github/workflows/security-scan.yml` runs weekly (Mon 02:00 UTC) via `zaproxy/action-baseline@v0.13.0`; `.zap/rules.tsv` suppresses known dev-only false positives; report uploaded as artefact.
**Status:** FIXED (2026-07-04)

### T2. Locust load tests - not written
**Gap:** No load test scenarios exist.
**Fix:** `load-tests/locustfile.py` with two user classes: `AnonymousUser` (browse catalogue, view product detail) and `AuthenticatedBuyer` (register, add to cart, list orders). 70/30 weight split.
**Status:** FIXED (2026-07-04)

### T3. Playwright E2E - not written
**Gap:** No end-to-end tests for critical buyer and supplier paths.
**Fix:** `playwright.config.ts` + three suites in `provena-web/e2e/`:
  - `browse-and-checkout.spec.ts` (anonymous browse, product detail, cart, checkout)
  - `supplier-order-management.spec.ts` (login, dashboard, order list, dispatch controls)
  - `admin-supplier-approval.spec.ts` (login, supplier list, approve/reject, audit log)
  All credential-dependent tests skip gracefully if env vars not set.
**Status:** FIXED (2026-07-04)

### T4. Frontend unit tests - zero coverage
**Gap:** No Vitest or React Testing Library tests in `provena-web`.
**Fix:** Vitest + RTL setup; `vitest.config.ts`, `src/test/setup.ts`; 14 tests passing across `pagination.test.tsx` (8 tests) and `product-card.test.tsx` (6 tests). `npm run test:unit` to run.
**Status:** FIXED (2026-07-04)

---

## 2FA enforcement

**Status:** FIXED (2026-07-04)
- TOTP authenticator app setup/enable/disable: backend endpoints already existed; frontend `/account/security` page now built.
- `totp_enabled` cookie set on login and token refresh; middleware enforces TOTP before admin and supplier routes, redirecting to `/account/security?enforce=1` if not set up.
- SMS/WhatsApp (NOT-04): optional per BRD, not implemented.

## Containerisation

**Status:** FIXED (2026-07-04)
- `provena-web/Dockerfile`: multi-stage (`deps`, `development`, `builder`, `runner`) using Next.js standalone output.
- Root `docker-compose.yml`: nginx, web, api, worker, beat, db, redis — production-ready with `restart: unless-stopped` and env var substitution.
- `docker-compose.dev.yml`: override for local dev (hot-reload mounts, exposed ports, dev settings).
- `nginx/nginx.conf`: routes `/api/` to Django, `/` to Next.js, WebSocket upgrade for HMR.

## Minor / deferrable

- MKT-07: Related products on product detail page
- MKT-08: Recently viewed products tracking
- ANA-04: Personalised homepage recommendations
- ANA-05: Cookie consent banner (required for UK GDPR analytics) — FIXED (2026-07-04): `CookieConsent` component with accept/decline, 365-day cookie, wired into root layout.
- NOT-04: SMS notifications (optional per BRD)
- PgBouncer not in `docker-compose.yml`
- Prometheus metrics endpoint not exposed
