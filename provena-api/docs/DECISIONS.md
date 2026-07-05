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
