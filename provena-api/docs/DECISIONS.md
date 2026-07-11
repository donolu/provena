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
