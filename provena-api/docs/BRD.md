# Business Requirements Document

**Product:** Provena
**Version:** 1.0
**Status:** Draft
**Owner:** Olumide Ibilaiye

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
| ORD-01 | Order statuses: pending payment, confirmed, processing, shipped, delivered, cancelled, refunded |
| ORD-02 | Multi-supplier cart: single checkout can include products from multiple suppliers |
| ORD-03 | Each supplier's items form a sub-order; Supplier sees only their sub-order |
| ORD-04 | Order confirmation email sent to Buyer and Supplier on payment success |
| ORD-05 | Buyer can cancel an order before it moves to processing |
| ORD-06 | Supplier marks orders as shipped and provides tracking reference |
| ORD-07 | Buyer can raise a dispute within 7 days of delivery; Admin mediates |
| ORD-08 | Returns initiated by Buyer; Supplier approves or rejects; refund processed by Admin |

### 4.7 Payments

| ID | Requirement |
|---|---|
| PAY-01 | Card payments via Stripe Checkout or Stripe Elements |
| PAY-02 | Raw card data never touches Provena servers; all card processing handled by Stripe |
| PAY-03 | Stripe webhook events used to confirm payment, handle failures, and process refunds |
| PAY-04 | Supplier payouts via Stripe Connect (platform model) |
| PAY-05 | Platform commission deducted from payout before transfer to Supplier |
| PAY-06 | Full refunds and partial refunds supported |
| PAY-07 | Payment history available to Buyer and Supplier in their respective dashboards |
| PAY-08 | Admin can issue manual refunds and adjust payouts with an audit trail |

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
- Automated logistics or delivery scheduling
- Multi-currency support
- Multi-language support
- B2B wholesale pricing tiers
- EDI integrations with suppliers

---

## 8. Assumptions and Constraints

- Payment processing exclusively via Stripe; no alternative PSP in scope
- Suppliers responsible for their own fulfilment and delivery
- Platform operator based in the UK; UK GDPR applies
- Initial deployment targets a single region (UK)
- Budget constrains infrastructure to managed cloud services (Render/Railway initially)
