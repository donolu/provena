# Business Requirements Document

**Product:** Provena
**Version:** 1.1
**Status:** Living document (reflects shipped platform as of 2026-07)
**Owner:** Olumide Ibilaiye

> Change log
> - **1.1 (2026-07)** - added the order pricing pipeline (VAT, per-supplier shipping, discount codes; ADR-012), platform-brokered delivery (ADR-013), GDPR erasure + data export (ADR-011), and per-item returns/admin refunds. Corrected the delivery scope in §7/§8. See `DECISIONS.md` for the architecture record.
> - **1.0** - initial draft.

---

## 1. Executive Summary

Provena is a multi-sided supply chain and marketplace platform for fresh produce. It connects suppliers and vendors with consumers through a managed storefront, while providing the operator with full visibility over inventory, stock levels, supplier relationships, and financials.

The platform has three sides:

- **Suppliers/Vendors** - farms, wholesalers, and distributors who list products and fulfil orders
- **Consumers/Buyers** - end customers who browse, purchase, and track deliveries
- **Platform Admin** - the operator who manages the marketplace, onboards suppliers, oversees compliance, and controls payouts

---

## 2. Problem Statement

Fresh produce supply chains are fragmented. Suppliers lack a modern, digital channel to reach buyers directly. Buyers have limited visibility into product origin, freshness, and availability. Existing generic marketplaces (Amazon, eBay) do not cater to the perishable goods workflow: lot tracking, expiry management, dynamic pricing by weight, and same-day or scheduled delivery.

Provena solves this by owning the full stack: supplier onboarding, product listing, real-time inventory, checkout, payment, and fulfilment tracking in a single platform.

---

## 3. Target Users

### 3.1 Supplier/Vendor

- Farm owner or distributor with produce to sell
- Needs: product catalogue management, order notifications, payout visibility, stock management
- Pain point: manual order-taking via phone/WhatsApp; no real-time inventory visibility

### 3.2 Consumer/Buyer

- Individual or business buyer of fresh produce
- Needs: browse by category, search by product, reliable delivery, order history
- Pain point: uncertainty about freshness, origin, and delivery timelines

### 3.3 Platform Admin

- Internal operator (Provena team)
- Needs: supplier onboarding and KYC, revenue dashboard, order dispute resolution, compliance reporting
- Pain point: managing supplier relationships manually at scale

---

## 4. Functional Requirements

### 4.1 Authentication and Authorisation

| ID | Requirement |
|---|---|
| AUTH-01 | Users register with email and password or via Google/Apple OAuth |
| AUTH-02 | All passwords hashed with bcrypt; minimum 12 characters enforced |
| AUTH-03 | Time-based one-time password (TOTP) two-factor authentication available to all users; mandatory for Admin and Supplier roles |
| AUTH-04 | Role-based access control with three roles: Admin, Supplier, Buyer |
| AUTH-05 | JWT access tokens (15-minute TTL) with refresh tokens (30-day TTL, rotated on use) |
| AUTH-06 | Session revocation on password change or explicit logout |
| AUTH-07 | Account lockout after 5 failed login attempts; unlocked after 30 minutes or by Admin |

### 4.2 Supplier and Vendor Management

| ID | Requirement |
|---|---|
| SUP-01 | Supplier self-registration with pending approval state |
| SUP-02 | Admin KYC workflow: document upload, review, approve or reject |
| SUP-03 | Supplier profile: business name, address, contact, certifications, description, logo |
| SUP-04 | Supplier manages their own product catalogue independently |
| SUP-05 | Supplier receives order notifications via email and in-app |
| SUP-06 | Supplier performance dashboard: total sales, average fulfilment time, return rate |
| SUP-07 | Supplier payout via Stripe Connect; configurable payout schedule |
| SUP-08 | Platform commission rate configurable per supplier or globally by Admin |

### 4.3 Product Catalogue

| ID | Requirement |
|---|---|
| CAT-01 | Products have: name, description, category, images (up to 8), unit type, price, weight |
| CAT-02 | Product variants supported (e.g. 500g, 1kg, 5kg bags) |
| CAT-03 | Category tree managed by Admin; Supplier assigns products to existing categories |
| CAT-04 | Full-text search across name, description, and category |
| CAT-05 | Filter by category, price range, supplier, availability, certifications |
| CAT-06 | Products have a status: draft, active, out of stock, archived |
| CAT-07 | Supplier can schedule products to go live at a future date and time |
| CAT-08 | Admin can suspend any product listing immediately |

### 4.4 Inventory and Stock Management

| ID | Requirement |
|---|---|
| INV-01 | Real-time stock quantity tracked per product variant |
| INV-02 | Stock can be adjusted manually by Supplier or via order fulfilment |
| INV-03 | Low-stock alert threshold configurable per product; notification sent to Supplier |
| INV-04 | Full audit trail: every stock change records timestamp, actor, reason, and quantity delta |
| INV-05 | Batch and lot tracking: each stock intake assigned a lot number and expiry date |
| INV-06 | Expiry alerts: notify Supplier N days before lot expiry (configurable) |
| INV-07 | Stock reservation: items reserved at cart-add and released if cart abandoned after 30 minutes |
| INV-08 | Admin can view stock levels across all suppliers |

### 4.5 Marketplace and Storefront

| ID | Requirement |
|---|---|
| MKT-01 | Public-facing storefront accessible without an account |
| MKT-02 | Featured products and categories on the homepage curated by Admin |
| MKT-03 | Shopping cart persists across sessions for logged-in users |
| MKT-04 | Wishlist: Buyer can save products for later |
| MKT-05 | Product reviews: Buyer can rate (1-5 stars) and review after a confirmed purchase |
| MKT-06 | Supplier ratings aggregated from product reviews |
| MKT-07 | Related products shown on product detail page |
| MKT-08 | Recently viewed products tracked per user |

### 4.6 Orders and Fulfilment

| ID | Requirement |
|---|---|
| ORD-01 | Sub-order lifecycle statuses: pending, confirmed, dispatched, delivered, cancelled (the parent order status is derived from its sub-orders) |
| ORD-02 | Multi-supplier cart: single checkout can include products from multiple suppliers |
| ORD-03 | Each supplier's items form a sub-order; Supplier sees and fulfils only their sub-order |
| ORD-04 | Order confirmation email sent to Buyer and Supplier on payment success |
| ORD-05 | Buyer can cancel an order (or a sub-order) before it is dispatched; stock is released |
| ORD-06 | Supplier marks a sub-order dispatched and provides a tracking reference |
| ORD-07 | Buyer can raise a dispute within the category's dispute window (1-7 days, default 3) of delivery; Admin mediates |
| ORD-08 | Returns: Buyer requests within 14 days of delivery selecting specific items/quantities; Supplier approves or rejects; refund and stock restock processed on approval |
| ORD-09 | Admin can refund selected items of any order directly; the refund is attributed to the supplier that sold each item and their payout is reversed proportionally |
| ORD-10 | Return eligibility is set by product type (ADR-014): perishable/exempt goods are `DEFECTIVE_ONLY` (no change-of-mind return; spoilage/defects go via a dispute), others are `RETURNABLE`. The policy is set per category (default defective-only for this produce marketplace), overridable per product, and snapshotted onto the order line at checkout. Change-of-mind returns of non-returnable items are blocked and the buyer is steered to raise a "damaged or spoiled" dispute |

### 4.7 Payments

| ID | Requirement |
|---|---|
| PAY-01 | Card payments via Stripe Checkout or Stripe Elements |
| PAY-02 | Raw card data never touches Provena servers; all card processing handled by Stripe |
| PAY-03 | Stripe webhook events used to confirm payment, handle failures, and process refunds |
| PAY-04 | Supplier payouts via Stripe Connect (platform model) |
| PAY-05 | Platform commission deducted from payout before transfer to Supplier |
| PAY-06 | Full refunds and partial (per-item) refunds supported; on refund of already-paid-out items the supplier's Stripe transfer is reversed proportionally so the platform does not absorb it |
| PAY-07 | Payment history available to Buyer and Supplier in their respective dashboards |
| PAY-08 | Admin can issue manual refunds (item-level, attributed to the selling supplier, or a platform-absorbed goodwill amount) and process/hold payouts, all with an audit trail |
| PAY-09 | Payout gross is the sub-order total; the platform commission is charged on discounted goods only (never on shipping); the fee rate is the supplier's `commission_rate` |

### 4.7a Pricing, Tax and Promotions

The order money path is a single deterministic pass at checkout, snapshotted onto the order so it is never recomputed from live config (see ADR-012 in `DECISIONS.md`).

| ID | Requirement |
|---|---|
| PRC-01 | Prices are VAT-inclusive. VAT is *extracted* from the gross line total per the product's VAT rate (standard 20%, reduced 5%, zero); receipts and supplier statements show the VAT breakdown |
| PRC-02 | Suppliers configure a shipping policy per account: flat rate, free-over-threshold, or per-item; shipping is added per sub-order and is itself VAT-inclusive at the standard rate |
| PRC-03 | Order-level discount codes: percentage or fixed amount, with minimum spend, validity window, and global and per-buyer usage caps |
| PRC-04 | A discount is allocated pro rata across sub-orders (and lines) by goods value; VAT is recomputed on the post-discount value |
| PRC-05 | Each code declares who funds it: PLATFORM (supplier paid on pre-discount goods, platform absorbs the discount) or SUPPLIER (supplier's payout gross is reduced by their share) |
| PRC-06 | Buyers can validate a code against their cart before checkout and see the previewed order total |
| PRC-07 | Rounding is defined: money is decimal, quantised to pence half-up; pro-rata splits use largest-remainder so parts sum exactly to the whole |

### 4.7b Delivery and Fulfilment Modes

| ID | Requirement |
|---|---|
| DEL-01 | Each supplier has a fulfilment mode: they ship themselves (default), or the platform brokers delivery via a third-party courier (ADR-013) |
| DEL-02 | For platform-brokered delivery, a courier quote is fetched at checkout and snapshotted as the delivery fee; an unserviceable address blocks that supplier's checkout with a clear reason rather than charging a wrong fee |
| DEL-03 | The courier is booked when the supplier marks the sub-order ready/dispatched; the buyer sees courier status and a tracking link |
| DEL-04 | The delivery fee is pass-through at cost; a reconciliation ledger records fee charged vs courier cost per delivery |
| DEL-05 | On a failed or cancelled courier delivery, the platform refunds the buyer's delivery fee and absorbs the courier cost |
| DEL-06 | The courier integration sits behind a swappable provider interface; a mock provider ships first, with a real courier adapter added later without changing the order flow |

### 4.7c Data Protection (UK GDPR)

| ID | Requirement |
|---|---|
| GDP-01 | Right to erasure: a user can request account erasure; personal data is anonymised in place while legally-required financial records (orders, payouts) are retained (ADR-011) |
| GDP-02 | Right to data portability (Article 20): a user can request a machine-readable export of their data, delivered via a time-limited secure link |
| GDP-03 | Cookie consent is collected before any analytics tracking; preferences stored per user |

### 4.8 Notifications

| ID | Requirement |
|---|---|
| NOT-01 | Transactional email for: registration, password reset, order confirmation, shipping update, payout received |
| NOT-02 | In-app notification centre with read/unread state |
| NOT-03 | Notification preferences managed by user (email on/off per event type) |
| NOT-04 | SMS notifications for order status changes (optional, toggled per user) |

### 4.9 Admin Dashboard

| ID | Requirement |
|---|---|
| ADM-01 | Platform overview: total revenue, active orders, registered users, top products |
| ADM-02 | Full user management: view, suspend, delete any account |
| ADM-03 | Supplier onboarding queue with KYC document review workflow |
| ADM-04 | Order management: view all orders, intervene in disputes, issue refunds |
| ADM-05 | Content management: homepage banners, featured categories, announcement banners |
| ADM-06 | Commission rate management per supplier and globally |
| ADM-07 | Financial reports exportable as CSV |
| ADM-08 | Audit log of all Admin actions |

### 4.10 Analytics and Personalisation

| ID | Requirement |
|---|---|
| ANA-01 | Sales reports: revenue by day/week/month, by supplier, by category |
| ANA-02 | Inventory reports: current stock levels, low-stock alerts summary, expiry calendar |
| ANA-03 | Buyer behaviour: most viewed products, cart abandonment rate, repeat purchase rate |
| ANA-04 | Personalised homepage recommendations based on purchase and browse history |
| ANA-05 | Cookie consent collected before any analytics tracking; preferences stored per user |
| ANA-06 | Privacy-first analytics tool (Plausible or PostHog self-hosted) preferred over Google Analytics |

---

## 5. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | API response time under 200ms at p95 under normal load |
| Availability | 99.9% uptime (less than 9 hours downtime per year) |
| Scalability | Architecture supports horizontal scaling to 10,000 concurrent users without redesign |
| Security | OWASP Top 10 mitigated; PCI DSS SAQ-A compliant; annual penetration test |
| Data residency | All data stored in UK/EU region |
| Accessibility | Frontend meets WCAG 2.1 AA |
| Browser support | Latest two versions of Chrome, Firefox, Safari, Edge |
| Mobile | Responsive web; native app out of scope for v1 |

---

## 6. Success Metrics (First 12 Months)

| Metric | Target |
|---|---|
| Suppliers onboarded | 50 |
| Monthly active buyers | 500 |
| Monthly gross merchandise value | £25,000 |
| Order fulfilment rate | 95% |
| Payment dispute rate | Under 2% |
| Platform uptime | 99.9% |

---

## 7. Out of Scope for v1

- Native mobile app (iOS/Android)
- Subscription or membership model for buyers
- Scheduled delivery windows and buyer per-order courier choice (on-demand platform-brokered delivery is in scope per ADR-013; scheduling is deferred)
- A live third-party courier adapter with real credentials (the swappable provider interface and a mock provider are in scope; the real adapter is deferred)
- Multi-currency support (GBP only)
- Multi-language support
- B2B wholesale pricing tiers
- EDI integrations with suppliers

---

## 8. Assumptions and Constraints

- Payment processing exclusively via Stripe; no alternative PSP in scope
- Suppliers are responsible for their own fulfilment by default; the platform may broker delivery via a third-party courier for suppliers configured for platform delivery (ADR-013)
- Suppliers are UK-established (per KYC); VAT handling assumes UK-inclusive pricing
- Platform operator based in the UK; UK GDPR applies
- Initial deployment targets a single region (UK); GBP only
- Budget constrains infrastructure to managed cloud services (Render/Railway initially)
