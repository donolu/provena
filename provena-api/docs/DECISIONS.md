# Architecture Decision Records

---

## ADR-001: Modular Monolith over Microservices

**Date:** 2026-06-30
**Status:** Accepted

**Context:**
At launch, Provena is operated by a single developer. The domain covers payments, inventory, catalogue, orders, suppliers, and notifications. Microservices would require service discovery, distributed tracing, inter-service authentication, independent CI/CD pipelines, and network calls where function calls currently suffice.

**Decision:**
Build as a modular monolith. Each business domain is a separate Django app with strict boundaries: inter-domain calls go through `services.py`, never direct model imports. This preserves the option to extract a service later without rewriting business logic.

**Consequences:**
Single deployment unit simplifies operations. When a specific domain (e.g. search, or a high-throughput notifications service) needs independent scaling, it can be extracted using the strangler fig pattern. This is a deliberate future choice, not a shortcut.

---

## ADR-002: Stripe as the Sole Payment Processor

**Date:** 2026-06-30
**Status:** Accepted

**Context:**
Payment processing requires PCI DSS compliance. Building compliance in-house or integrating multiple PSPs adds significant engineering and regulatory overhead.

**Decision:**
Stripe exclusively, using Stripe Elements or Stripe Checkout so card data never touches Provena servers. Supplier payouts via Stripe Connect. This reduces PCI DSS scope to SAQ-A.

**Consequences:**
Stripe's 1.4% + 20p UK card fee applies to every transaction. If margins require a cheaper PSP (e.g. GoCardless for direct debit, or Adyen at scale), a payment abstraction layer in `payments/services.py` will minimise the migration surface.

---

## ADR-003: Separate Frontend and Backend Repos

**Date:** 2026-06-30
**Status:** Superseded by ADR-007

**Context:**
Django and Next.js have different deployment cycles, different languages, different CI requirements, and would be deployed to different services (Render for API, Vercel for frontend).

**Decision:**
`provena-api` and `provena-web` are separate repositories. They communicate exclusively through the versioned REST API. No shared code between repos except OpenAPI schema (generated from the API, consumed by the frontend).

**Consequences:**
Each repo has its own CI, versioning, and deployment pipeline. API changes that are breaking to the frontend must be communicated and coordinated. OpenAPI client generation (e.g. `openapi-typescript-codegen`) will be introduced to keep types in sync.

---

## ADR-004: PostgreSQL over NoSQL

**Date:** 2026-06-30
**Status:** Accepted

**Context:**
The data model has strong relational structure: orders contain sub-orders containing items; products have variants; suppliers own products. Inventory requires ACID transactions (stock reservation must not double-count under concurrent requests).

**Decision:**
PostgreSQL 16. JSONB columns used for flexible product attributes (e.g. nutritional info, certifications) where the schema is legitimately variable. Elasticsearch or Typesense introduced for search when full-text search in PostgreSQL becomes the bottleneck.

**Consequences:**
Single database to operate and back up. PostgreSQL's row-level locking handles stock reservation correctly. If search at scale requires Elasticsearch, the product data is synced via a Celery task (not a direct query), keeping the two stores independent.

---

## ADR-005: UUID Primary Keys on User-Facing Resources

**Date:** 2026-06-30
**Status:** Accepted

**Context:**
Sequential integer primary keys in URLs allow enumeration attacks: a user can iterate `/orders/1/`, `/orders/2/` to probe for other users' orders. Object-level permission checks defend against this, but defence-in-depth is preferable.

**Decision:**
UUID v4 primary keys on all models that appear in API responses or URLs: User, Supplier, Product, Order, Payment, Notification. Internal join tables (OrderItem, StockAuditLog) use sequential integer PKs for performance.

**Consequences:**
Slightly larger index size. No meaningful performance impact at the expected data volumes. URL paths are non-guessable.

---

## ADR-006: Render over AWS for Initial Deployment

**Date:** 2026-06-30
**Status:** Accepted

**Context:**
AWS offers the most scalable infrastructure but requires significant operational investment: VPCs, IAM roles, ECS task definitions, RDS parameter groups, etc. For a product that has not yet validated its market, that investment is premature.

**Decision:**
Render for API and Celery workers; Render managed PostgreSQL and Redis; Vercel for the Next.js frontend. Cloudflare in front of everything for DNS, TLS, and basic DDoS protection.

**Consequences:**
Lower operational overhead. Render's pricing is higher per compute unit than raw AWS, but the engineering time saved at this stage is worth more. Migration path to AWS is documented in the TRD (infrastructure section) and does not require application code changes.

---

## ADR-007: Monorepo over Separate Repositories

**Date:** 2026-07-04
**Status:** Accepted (supersedes ADR-003)

**Context:**
ADR-003 assumed that `provena-api` and `provena-web` would have independent deployment cycles and separate CI pipelines, justifying separate repositories. In practice, both services are always deployed together: a backend change almost always has a corresponding frontend change, and a single developer owns both. The separate-repo model created real friction: deployment configuration (`docker-compose.yml`, Nginx, load tests, OWASP ZAP config) had nowhere to live and was left untracked on disk; pre-commit hooks could not be installed at the git root because there was no root git repo; CI workflows were duplicated. The first time a root-level `docker-compose.yml` was created, it could not be committed to either repository.

**Decision:**
Migrate to a single monorepo (`donolu/provena`) using `git subtree add` to preserve the complete commit history of both `provena-api` and `provena-web`. Deployment configuration lives at the repo root. CI workflows for each sub-project live in the single root `.github/workflows/` directory, gated by `paths:` filters. Pre-commit runs from the root with `files:` patterns scoping hooks to the correct subdirectory.

**Consequences:**
`donolu/provena-api` and `donolu/provena-web` are archived (read-only). Full commit history for both projects is navigable in the monorepo via `git log provena-api/` and `git log provena-web/`. The assumption in ADR-003 about independent deployment cadences is revisited: if a future hire takes ownership of one layer and the teams genuinely diverge, the sub-projects can be extracted using `git subtree split` with full history intact. OpenAPI client code generation (planned, see backlog) will run from the monorepo root, writing generated types into `provena-web/src/lib/api/generated/`.

---

## ADR-008: Dispute Resolution Design

**Date:** 2026-07-05
**Status:** Accepted

**Context:**
Provena is a multi-supplier marketplace where a single buyer order may involve several suppliers. Disputes about order quality, non-delivery, or fraudulent claims can arise from either side. The design must balance three competing needs: fast resolution for time-sensitive goods (fresh produce can spoil within days), supplier protection against frivolous or fraudulent buyer claims, and a clear audit trail for financial reconciliation.

**Decision:**

**Bidirectional disputes.** Either the buyer or the supplier can open a dispute against a sub-order. This is a deliberate departure from the more common buyer-only model. Suppliers on a fresh-produce marketplace face real risk from delivery-refusal fraud and false claims; a system that only lets buyers complain would be asymmetric and undermine supplier trust.

**Transparent event log.** All dispute events (opened, response, escalation, admin notes, resolution) are written to an append-only `DisputeEvent` table and are readable by both parties and admin. Neither party has a private channel. Transparency is the primary mechanism for deterring frivolous claims on both sides.

**Category-scoped dispute window for condition claims.** The window within which a condition-based dispute (damaged, spoiled, wrong item, partial delivery) can be raised is stored on the `Category` model as `dispute_window_days` (integer, min 1, max 7). This means the window is configurable per product type without a code change: fresh produce might carry a 2-day window, dry goods a 7-day window. A fixed-code list of windows per product type was rejected because it would require a deploy whenever a new category was introduced. A global setting was rejected because it cannot distinguish between perishable and non-perishable goods. Non-delivery and supplier counter-claim disputes use a fixed 14-day window regardless of category, since perishability is not a factor.

**Interim window start.** Until order fulfilment tracking (#21) provides a confirmed delivery timestamp, the dispute window starts from the order placement date plus `dispute_window_days`. This is acknowledged as an approximation; the dispute service will be updated to use the actual delivery timestamp once tracking is in place.

**Admin-triggered refund, not automated.** When admin resolves a dispute with a refund outcome, the refund is not triggered automatically. Admin must explicitly call the refund endpoint, which calls Stripe and creates a `DisputeRefund` record. Automatic refund on resolution was rejected for v1 because: (a) Stripe Connect (#18) is not yet implemented, so refunds flow from the platform account and the accounting between platform and supplier must be manually verified; (b) partial refund amounts require a human judgement step; (c) the risk of an automated code path issuing unintended refunds outweighs the convenience saving at current dispute volumes.

**Payout hold on open disputes.** When a dispute is opened against a sub-order, that sub-order's payout to the supplier is held and excluded from the next payout run. This eliminates the need for clawbacks in the common case where disputes are raised before the supplier's payout settles. If a dispute is raised after a payout has already processed, a clawback record is created against the supplier's next payout run.

**Commission reversal.** The platform commission on a refunded sub-order is reversed for the refunded portion. The `DisputeRefund` record carries the sub-order FK and amount, which is sufficient for the payout service to calculate and subtract the commission portion from the platform revenue ledger.

**Consequences:**
The bidirectional model requires the dispute type taxonomy to cover both buyer and supplier grievances, adding some UI and API complexity compared to a buyer-only flow. The category-scoped window requires `dispute_window_days` to be set correctly when new categories are created; an omission (defaulting to 3 days) is a safe fallback rather than a breaking state. The manual refund step adds latency for buyers waiting on a refund decision; this is an acceptable trade-off at launch volumes and will be revisited when Stripe Connect is implemented. The payout hold approach assumes disputes are typically raised before payout; if payout cycles become very short (e.g. daily), the clawback path will be exercised more frequently and may need its own tooling.

---

## ADR-009: End-to-End Testing with Playwright against the Docker Compose Stack

**Date:** 2026-07-10
**Status:** Proposed

**Context:**
Provena's automated tests currently sit at two levels: the API suite (`pytest`, run in `api.yml`) exercises Django in isolation, and the web suite (`vitest`, run in `web.yml`) exercises React components and units with the network layer mocked. Both are fast and valuable, but by construction each mocks the other side of the HTTP boundary. The defects that survive both are integration defects that live at the seams between the two stacks:

- **Authentication flow.** Login returns a short-lived access token in the body and a rotating refresh token in an HttpOnly cookie (`provena_rt`); the frontend refreshes silently against `/api/v1/auth/refresh/`. A regression in cookie attributes, CORS, or the Nginx proxy can break real sessions while every unit test still passes.
- **Contract drift.** The frontend consumes a TypeScript client generated from the API's OpenAPI schema (ADR-007, `generate-client` job). A schema change that is not regenerated, or a field rename, is invisible to unit tests on either side but breaks the running app.
- **Reverse-proxy routing.** Nginx routes `/api/` to Django and everything else to Next.js. Path, header, and SSR/ISR behaviour is only exercised when the whole stack runs together.
- **Payment and multi-actor journeys.** Checkout, supplier dispatch, and admin approval span several services and roles end to end.

Playwright specs for the three critical journeys already exist in `provena-web/e2e/` (browse-and-checkout, supplier-order-management, admin-supplier-approval) with a shared auth helper. They do **not** run in CI: `playwright.config.ts` sets no `webServer` under CI, and each spec calls `test.skip` when its `E2E_{ADMIN,BUYER,SUPPLIER}_EMAIL/PASSWORD` credentials are unset. The result is E2E test code that never executes, which gives false confidence and will bit-rot. Issue #20 tracks closing this gap.

**Decision:**

**Run Playwright against the full Docker Compose stack in a dedicated `e2e.yml` workflow.** The workflow brings up the same `docker-compose.yml` + `docker-compose.dev.yml` stack used for local development (Nginx, PostgreSQL, Redis, Django, Celery worker, Next.js), waits on the API health check, runs `npm run test:e2e` against the Nginx entrypoint via `E2E_BASE_URL`, and tears the stack down. Running against real Compose, rather than a mocked backend or a bespoke lightweight harness, is the whole point: it exercises the production-parity seams above. A mocked backend was rejected because it reintroduces the blind spot E2E exists to cover; a bespoke harness was rejected because it would drift from how the app is actually deployed.

**Seed a deterministic fixture and supply role credentials.** A management command seeds a buyer, supplier, and admin account plus a minimal catalogue, and the three `E2E_*_EMAIL/PASSWORD` pairs are provided as CI secrets so the existing `test.skip` guards deactivate and the specs actually run. This keeps the tests self-contained and repeatable rather than dependent on ambient data.

**Gate to pull requests into `main`, not every push.** The stack boot plus browser run is slow and resource-heavy relative to the unit suites, so it runs on `pull_request` to `main` and `workflow_dispatch`, not on every branch push. The existing CI config is retained: `retries: 2`, `workers: 1`, `trace: 'on-first-retry'`, `screenshot: 'only-on-failure'`, and the `github` reporter. Traces and screenshots are uploaded as workflow artefacts so failures are debuggable without reproduction.

**Introduce as a non-blocking check first, then promote to required.** The job runs informationally at first to gather flake data against the branch-protection model (which treats each job as an individual required check). Once stable it is added to the required checks on `main`. This avoids a flaky new gate blocking unrelated work on day one.

**Keep E2E at the top of the pyramid.** E2E complements, and does not replace, the unit and API suites. Coverage is deliberately limited to a small set of high-value journeys; broad behaviour stays in the faster lower layers.

**Consequences:**
PR CI gains several minutes of wall-clock time on changes that touch the app, since the Compose stack must boot before tests run. A seed fixture and its teardown must be maintained, and CI secrets for the seeded accounts must be managed. Because E2E is tied to Compose, drift in the Compose definition surfaces early as an E2E failure, which is desirable. Playwright is inherently more flake-prone than unit tests; the retry, trace, and artefact settings mitigate this, and the staged non-blocking-then-required rollout limits disruption while confidence is established. The alternative of leaving the specs skipped was rejected: unexecuted tests are worse than no tests because they imply coverage that does not exist.

---

## ADR-010: PgBouncer Connection Pooling

**Date:** 2026-07-11
**Status:** Accepted

**Context:**
Django opens a database connection per worker process (and, with `CONN_MAX_AGE`, holds it open). Under Daphne/Celery at higher concurrency this multiplies quickly and exhausts PostgreSQL's `max_connections` (default ~100), which becomes a hard ceiling well before the application itself is saturated. This is required before scaling beyond roughly 50 concurrent API workers (#12).

**Decision:**

**PgBouncer in transaction pooling mode**, fronting PostgreSQL. Self-hosted deployments run an `edoburu/pgbouncer` sidecar in `docker-compose.yml` (listening on `:6432`); Render's managed Postgres provides PgBouncer natively. The application, Celery worker, and beat all connect through the pooler (`DATABASE_URL` → `pgbouncer:6432`).

Transaction pooling was chosen over session pooling because it returns a server connection to the pool at the **end of each transaction** rather than at disconnect, so a large fleet of client connections multiplexes onto a small pool of server connections — exactly the fan-in needed. Session pooling would pin a server connection for the life of each client and give little benefit here.

Transaction pooling reassigns a backend between transactions, so anything bound to a single server connection is incompatible and is disabled:
- **Server-side cursors** (`DISABLE_SERVER_SIDE_CURSORS = True`).
- **psycopg server-side prepared statements** (`OPTIONS = {"prepare_threshold": None}`).

Both are applied automatically for PostgreSQL and are harmless on a direct connection. `LISTEN/NOTIFY` and session-level `SET` are likewise avoided in application code.

**Migrations use a direct connection** (`DIRECT_DATABASE_URL` → Postgres `:5432`), not the pooler: DDL, `CREATE INDEX CONCURRENTLY`, and advisory locks are unsafe under transaction pooling. CI and the documented commands run `migrate` with `DATABASE_URL` overridden to the direct URL.

DB credentials in Compose are env-driven (`DB_USER` / `DB_PASSWORD` / `DB_NAME`, defaulting to `provena`) so the same definitions front Postgres, PgBouncer, and the application URLs without duplication.

**Consequences:**
Database connections now scale to hundreds of workers against a small server pool, removing the `max_connections` ceiling as the near-term scaling limit. The cost is a small per-query overhead from disabling prepared statements (acceptable at current volumes; revisit if profiling shows it matters) and a second connection string to manage. Migrations must remember the direct URL — enforced in CI and Compose, and documented in `deployment.md`. PgBouncer is one more moving part, but it is off-the-shelf, stateless, and low-maintenance. The transaction-pooling constraints (no server-side cursors/prepared statements) are a permanent design rule for this codebase, not a temporary workaround.

## ADR-011: Account Erasure by Anonymisation

**Date:** 2026-07-12
**Status:** Accepted

**Context:**
UK GDPR Article 17 gives users the right to erasure. Provena already offers data **export** (#41). The complication is that a buyer's `User` row is referenced by orders and payments under `on_delete=PROTECT`, and those financial records must be retained to meet tax, accounting, and anti-fraud obligations. A hard delete is therefore impossible without destroying records we are legally required to keep, and cascading the delete would be unlawful.

**Decision:**
Implement erasure as **anonymisation**, not deletion (`POST /api/v1/auth/me/delete/`, `services.erase_account`).

On erasure we: blacklist every outstanding refresh token; delete the user's saved addresses (directly identifying); and scrub the `User` row in place — email set to `deleted-<id>@deleted.invalid`, names cleared, password made unusable, TOTP disabled, `is_active=False`, and `erased_at` timestamped. The row survives so orders/payments stay referentially intact, but it no longer identifies a person; the original email is freed for reuse.

The action **re-authenticates** the caller (current password, plus the TOTP code when 2FA is enabled) to prevent hijacked-session or CSRF-driven deletion. It is restricted to **buyer** accounts in this iteration; suppliers and admins have business/financial entanglements (KYC, Connect payouts, listings) and are directed to support. Order shipping snapshots are retained under legal basis and documented as such in the privacy policy.

**Consequences:**
- Erasure is compliant and reversible-proof (data is gone) without breaking retained financial records.
- Suppliers/admins are out of scope for self-service erasure for now; a follow-up can handle the supplier lifecycle.
- Retained order snapshots still contain shipping details entered at purchase time; a later pass can anonymise those beyond the statutory retention window.

## ADR-012: Order Pricing Pipeline (Shipping, VAT, Discounts)

**Date:** 2026-07-16
**Status:** Accepted

**Context:**
Today an order's price is only the goods subtotal. `orders.services.create_order` sums `variant.price * quantity` into `Order.total_amount` and per-supplier `SubOrder.subtotal`; `payments.services.create_payment_intent` charges `order.total_amount`; and `_create_payouts` pays each supplier `subtotal` minus a flat `PLATFORM_FEE_PERCENT`. There is no shipping (#140), no VAT accounting (#141), and no discount codes (#142). For a UK marketplace this is both a commercial gap (we cannot charge delivery or run promotions) and a compliance gap (no VAT breakdown on receipts, no basis for a supplier's VAT return).

The three features all mutate the same money path and interact: a discount changes the VAT base, shipping is itself taxed, and payouts must reflect all three. Building them ad hoc would produce rounding drift between the charged total and the sum of the payouts, and an order that cannot be reconstructed once live config moves on. This ADR settles the pipeline once so the three issues slot into it rather than each re-opening the money path.

**Decision:**

1. **One deterministic pipeline, computed at checkout and snapshotted.** Pricing is computed in a single pass and the results are stored on the order; nothing is recomputed later from live product, shipping or VAT config, which changes over time. Order of operations, per sub-order (one supplier):
   1. `goods_subtotal` = sum of `unit_price * quantity` over the lines
   2. `discount_amount` = the order discount allocated to this sub-order (see 4)
   3. `shipping_amount` = the supplier's shipping rule applied to the sub-order (see 3)
   4. `sub_order.total` = `goods_subtotal - discount_amount + shipping_amount`
   5. `vat_amount` = the VAT component extracted from the post-discount goods and the shipping (see 2)

   `Order.total_amount` = the sum of the `sub_order.total` values. The charged amount is always the sum of the stored parts, so the PaymentIntent, the payouts and any refund reconcile to the penny by construction.

2. **VAT is inclusive and per line; the supplier is the merchant of record.** Listed prices are VAT-inclusive (the UK B2C norm), so accounting for VAT does not change what the buyer pays: VAT is *extracted* from the gross for the receipt and for the supplier's VAT return, not added on top. Each product carries a VAT rate (STANDARD 20% / REDUCED 5% / ZERO), defaulting to STANDARD and snapshotted onto `OrderItem` at checkout; VAT on shipping follows the standard rate. Each supplier is the principal for their own goods and the platform acts as agent, collecting through Stripe Connect and rendering a VAT breakdown per sub-order under the supplier's VAT details, plus its own VAT invoice to the supplier for commission. Non-UK-established sellers, where marketplace "deemed supplier" rules would make the platform liable, stay out of scope; suppliers remain UK-established per KYC.

3. **Shipping is per supplier.** Each supplier owns a shipping policy (flat rate, free over a threshold, or per-item), stored on the supplier and snapshotted per sub-order at checkout. Shipping revenue belongs to the supplier who fulfils, so it is added to that supplier's payout gross in full; platform commission is charged on goods only, never on shipping. This assumes the supplier fulfils their own delivery. So that a future platform-brokered courier model (a third party delivers and is paid separately) does not re-open the money path, the payout logic reads *who the shipping money is attributed to* off the snapshot rather than assuming it is always the supplier; #140 must not hard-code shipping into supplier payout gross. See ADR-013.

4. **Discounts are order-level codes, allocated pro rata, with explicit funding.** A `DiscountCode` (percentage or fixed amount, with minimum spend, a validity window, and global plus per-buyer usage limits) reduces the goods subtotal and is allocated across sub-orders in proportion to their goods value. A `DiscountRedemption` row records each use for enforcement and idempotency. Each code declares `funded_by`: PLATFORM (the supplier is paid on pre-discount goods and the platform absorbs the discount out of its fee) or SUPPLIER (the supplier's payout gross is reduced by their allocated share). Free-shipping thresholds are evaluated on the pre-discount goods value.

5. **Rounding is defined, not incidental.** Money stays `Decimal`, quantised to 0.01 with ROUND_HALF_UP at each stored boundary. Pro-rata allocations (the discount split, and any future split) use the largest-remainder method so the parts sum exactly to the whole, with no lost or invented pennies.

6. **Data model.** Add breakdown columns `goods_subtotal`, `discount_amount`, `shipping_amount` and `vat_amount` to `Order` and `SubOrder` (keeping `total_amount` / `subtotal`); snapshot `vat_rate` and `vat_amount` onto `OrderItem`; add a VAT-rate field to `Product`; add a shipping policy to `Supplier`; and add `DiscountCode` and `DiscountRedemption`. Payout gross becomes `sub_order.total - platform_fee`, where the fee is based on the discounted goods (excluding shipping) and the fee source moves from the global `PLATFORM_FEE_PERCENT` to the supplier's existing but currently-unused `commission_rate`, with the setting as the default.

7. **Sequencing.** Land it safe-to-risky, as the pipeline implies: **#141 VAT first** (inclusive, so it changes neither totals nor payouts: lowest risk, and it unlocks receipts and the breakdown columns), then **#140 shipping** (which changes totals and payout gross), then **#142 discounts** (allocation, funding and redemption: the most involved). Each ships behind the same pipeline function.

**Consequences:**
- The charged total, the payouts and any refund reconcile by construction, and the order becomes a self-contained financial snapshot independent of later config changes.
- `create_order`, `create_payment_intent`, `_create_payouts` and the refund path all move to consume the stored breakdown; refunds become breakdown-aware (refunding the correct VAT and shipping proportion and reversing the right transfer share), tracked within #140 and #142.
- Suppliers gain a shipping-policy surface and a `commission_rate` that finally drives payouts; the global setting becomes only the default.
- Per-sub-order VAT breakdowns and per-supplier VAT numbers become new onboarding and KYC requirements; B2B VAT-exclusive invoicing and non-UK sellers are explicitly deferred.
- Existing orders predate the breakdown columns, so a data migration backfills `goods_subtotal = subtotal`, zero shipping and discount, and VAT extracted at the standard rate, so historical receipts still render.

**Addendum (2026-07-17): implementation refinements as the three issues landed.** The pipeline was built in the ADR's safe-to-risky order and settled three details the original decision left implicit:

- **VAT base under discounts (#142).** VAT is extracted from the **post-discount** goods value. To keep mixed VAT rates correct within one sub-order, the order discount is allocated by largest remainder twice: order → sub-order (by goods value), then sub-order → line (by line value); per-line VAT is then extracted on the post-discount line value and summed. Item, sub-order and order VAT reconcile by construction.
- **Funding → payout split (#142).** SUPPLIER-funded: payout gross is the sub-order total (`goods − discount + shipping`) and commission is on the discounted goods. PLATFORM-funded: the supplier is paid on **pre-discount** goods (`gross = goods + shipping`, commission on full goods) and the platform absorbs the discount out of its fee. The funding source and code are snapshotted on the order (`discount_funded_by`, `discount_code`) so payouts never depend on live `DiscountCode` config. Redemption is one-row-per-order (idempotent) with the code row locked `FOR UPDATE` at checkout so usage caps cannot be over-redeemed.
- **Deferred: platform-funded VAT base.** Following this ADR, VAT is extracted from the discounted price even when the platform funds the discount. The HMRC treatment of third-party-funded discounts (which may not reduce the supplier's VAT base) is a known refinement left out of scope for now, alongside the ADR's existing B2B / non-UK-seller deferrals. Suppliers remain UK-established per KYC.
- **Commission source (#140).** The payout fee moved off the global `PLATFORM_FEE_PERCENT` to the supplier's `commission_rate` (the setting is now only the default), and is charged on goods only, never on shipping.
- **Breakdown-aware refunds (#191, #198).** A return refunds its sub-order's own total, and the supplier's Stripe transfer is reversed proportionally (`ratio = refund / sub_order.subtotal`). Returns are now **per-item** (#198): a buyer returns specific items/quantities; the refund is the returned units' discounted, VAT-inclusive value with the discount allocated pro rata by returned goods value; shipping is refunded only when the whole sub-order is returned in one request; only the returned units restock. A return with no items = a full sub-order return.

---

## ADR-013: Platform-Brokered Delivery (Third-Party Courier)

**Date:** 2026-07-16 (proposed); first slice **Accepted** 2026-07-17.
**Status:** Accepted (first slice — architecture; live courier deferred)

**Context:**
ADR-012 §3 assumes a supplier fulfils their own delivery: the shipping fee is the supplier's revenue and is added to their payout gross in full. Some suppliers have no delivery capability of their own (the "Lidl" case). To serve them, the platform would broker a third-party courier (Uber Direct / Stuart-style, Tesco Whoosh-like same-day), quote the fee at checkout, and have the courier deliver. This is not another entry in the flat/free-over/per-item shipping menu; it is a different fulfilment model with a different money path and a different merchant of record, so it gets its own decision rather than being smuggled into #140.

**First slice — Accepted (#194, 2026-07-17):** the *architecture*, with a platform-configured flat fee instead of a live courier quote.
- **Per-supplier, admin-set fulfilment mode.** `Supplier.fulfilment_mode` = `SUPPLIER_SHIP` (default) | `PLATFORM_DELIVERY`, plus a `platform_delivery_fee` (flat). Platform-brokered delivery is a commercial arrangement the platform configures; the supplier sees it read-only. Snapshotted per sub-order (`SubOrder.fulfilment_mode`).
- **Attribution off the snapshot.** `PLATFORM_DELIVERY` shipping lands in the buyer's total (VAT extracted at the standard rate as before) but is **excluded from the supplier's payout gross** — `_create_payouts` computes `gross = commission_base + supplier_shipping`, where `supplier_shipping` is the shipping for `SUPPLIER_SHIP` and `0` for `PLATFORM_DELIVERY`. The platform keeps the fee. This is exactly the ADR-012 §3 forward-compat contract.
- **Pass-through at cost, no margin line.** The buyer's delivery fee equals the platform's configured cost; there is no delivery-margin accounting line in this slice.
- **VAT principal.** For the delivery leg the platform is the principal (standard-rated). The money math is unchanged; the split VAT invoice (supplier VAT number on goods, platform VAT on delivery) is a **deferred refinement**.
- **Refunds compose unchanged.** `reverse_payout_for_sub_order` reverses `payout.net`, which now excludes platform-delivery shipping, so a return reverses only the supplier's goods share; the platform absorbs the delivery-fee refund (failed-delivery/courier-cost reconciliation deferred).

**Deferred to the live-courier slice:** a real courier API + live quotes, serviceability checks + fallback, quote expiry/refresh, courier dispatch/billing + failed-delivery refunds, a delivery-margin line, buyer per-order delivery choice, and the split VAT invoice. The open questions below are settled only insofar as the flat-fee architecture requires; they remain open for the live-courier work.

**Second slice — live courier, built against a mock (#202, 2026-07-18).** A provider-agnostic `CourierProvider` interface (`apps/delivery`) with a `MockUberDirectProvider` (Uber-Direct-shaped, deterministic, no creds) — a real Uber Direct / Stuart adapter is a drop-in via `settings.COURIER_PROVIDER`. The open questions are now settled (decisions made deliberately, documented here):
- **Serviceability.** From the provider's quote call. An unserviceable `PLATFORM_DELIVERY` supplier **blocks checkout for that supplier** with a clear reason (`place_order` raises) — never a silent wrong charge. Auto-fallback to self-ship is deferred (a platform-delivery supplier has no reliable own policy to fall back to).
- **Quote lifecycle.** The quote (provider id, fee, expiry) is snapshotted onto a `CourierDelivery` row and becomes the sub-order `shipping_amount`; `create_payment_intent` **rejects an expired quote** ("check out again") rather than charging a stale price. Auto re-quote-and-continue deferred.
- **Margin.** **Pass-through at cost** (no margin line); `CourierDelivery` records buyer fee vs courier cost (equal under pass-through) as a reconciliation ledger.
- **Dispatch trigger.** The courier is **booked when the supplier marks the sub-order dispatched** (parcel ready), not on payment — so a courier isn't sent to an unpacked order. On-demand.
- **Failed/cancelled delivery.** On a courier failure/cancellation webhook the platform **refunds the buyer's delivery fee and absorbs the courier cost**; the row is flagged. Auto-retry deferred; the goods refund still follows the normal returns/dispute path.
- **Billing/settlement.** The courier is billed via its **own API** (the mock records `courier_cost`), paid out-of-band by the platform — not via Stripe Connect. `CourierDelivery` is the ledger; `GET /api/v1/delivery/admin/reconciliation/` + Django admin summarise it. Webhook signature verification is deferred to the real adapter.
- **VAT** (from slice 1, unchanged): the platform is principal for the delivery leg (standard-rated); the split VAT invoice stays deferred.

Still deferred after this slice: the real provider adapter + credentials, webhook signature verification, self-ship fallback, re-quote-and-continue, delivery margin, auto-retry, scheduled windows, buyer per-order courier choice, a dedicated admin reconciliation page.

**Decision (to be settled):**
The direction, with the details deferred until the base pipeline (#140/#141/#142) has shipped:

1. **A per-sub-order fulfilment model.** `SUPPLIER_SHIP` (ADR-012 today: supplier's own policy, fee attributed to the supplier) versus `PLATFORM_DELIVERY` (a courier quote, fee attributed to the platform). The ADR-012 snapshot columns (`shipping_amount`) are reused unchanged; only the *attribution* of the shipping money differs. ADR-012 §3 already requires payout logic to read attribution off the snapshot, so this slots in without re-opening the money path.

2. **The delivery fee is a pass-through, not supplier income.** Under `PLATFORM_DELIVERY` the fee must not enter the supplier's payout gross. The buyer pays it, the platform collects it, and the platform remits to the courier. A courier billed through its own API is not a Stripe Connect account, so this is not a three-way Connect split: it is platform revenue in and a courier cost out, a leg the platform owns.

**Open questions:**
- **VAT.** For the delivery leg the platform is likely the principal / merchant of record (a standard-rated service), which is a different principal than ADR-012's "supplier is principal for goods and their own shipping". How does this render on the receipt and the platform's VAT return?
- **Quote lifecycle.** Courier quotes are time-bound (valid ~minutes). How are expiry and refresh handled between checkout and payment confirmation, and what happens when a snapshotted quote has lapsed by capture?
- **Serviceability.** Not every address is deliverable same-day. Where does the serviceability check run, and on failure do we fall back to `SUPPLIER_SHIP` / standard shipping or block the line?
- **Margin.** Does the platform pass the courier fee at cost or mark it up? Commercial call, but it changes whether there is a delivery-margin line to account for.
- **Refunds.** How does a cancelled or failed delivery reconcile against a courier already dispatched and billed?

**Consequences (anticipated):**
- Suppliers with no delivery capability become servable, widening supply.
- The platform takes on a new operational and financial relationship (courier billing, SLAs, failed-delivery handling) and a delivery-leg VAT position it did not have before.
- The money path gains a third recipient class (external couriers) distinct from suppliers on Connect.
