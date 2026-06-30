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
**Status:** Accepted

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
