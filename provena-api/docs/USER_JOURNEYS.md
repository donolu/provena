# User Journey Flows

**Product:** Provena
**Status:** Living document (2026-07)
**Audience:** product, design, engineering, QA

Provena has three actors: **Buyer**, **Supplier**, and **Admin** (plus **System**: Stripe, the courier provider, Celery jobs). This document narrates the primary journeys and the state each one moves through. Flow diagrams are maintained in `docs/diagrams/provena-diagrams.drawio` (one tab per diagram); export each tab to `docs/diagrams/` and it renders inline where referenced (see `diagrams/README.md`).

> Tabs → exported PNGs:
> - **Checkout money path** → `docs/diagrams/journey-checkout.png`
> - **Order lifecycle** → `docs/diagrams/journey-order-lifecycle.png`
> - **Returns and refund attribution** → `docs/diagrams/journey-returns-refund.png`

---

## 1. Buyer

### 1.1 Discover and register
1. Land on the public storefront (no account needed): browse categories, search, view product and supplier pages.
2. Add variants to the cart. Cart persists by session for guests, by account when logged in; adding an item places a **stock reservation** with a 30-minute TTL.
3. Register (email + password) or log in. Admin and Supplier roles require TOTP 2FA; Buyers may opt in.

### 1.2 Checkout (money path)

![Checkout flow](./diagrams/journey-checkout.png)

| Step | Actor | What happens |
|---|---|---|
| 1 | Buyer | Reviews cart, enters/selects a delivery address |
| 2 | Buyer | Optionally enters a discount code; `POST /discounts/validate/` previews the discount and the **new total** without reserving anything |
| 3 | Buyer | Places the order. `place_order` groups items by supplier into sub-orders, runs the one-pass pricing (goods → discount → shipping → VAT), and for platform-delivery suppliers fetches a courier quote |
| 3a | System | An **unserviceable** courier address blocks that supplier's checkout with a clear reason (no wrong charge) |
| 4 | System | `create-intent` creates the Stripe PaymentIntent for `order.total_amount`; a stale/expired courier quote is rejected ("please checkout again") |
| 5 | Buyer | Confirms card payment in Stripe Elements |
| 6 | System | Stripe webhook `payment_intent.succeeded` confirms the order; confirmation emails go to Buyer and each Supplier |

The price shown at every step equals `order.total_amount`; the Pay button charges exactly that.

### 1.3 Track, receive, and (if needed) return

![Order lifecycle](./diagrams/journey-order-lifecycle.png)

- Track each sub-order's status live over the order WebSocket (`ws-ticket/`). For platform-delivered sub-orders a courier tracking link is shown.
- **Cancel** before dispatch releases the reserved stock and (if paid) refunds.
- **Return** within 14 days of delivery: select specific items/quantities and a reason; the Supplier approves or rejects; on approval the refund is issued and the returned units restock.
- **Dispute** within the category's dispute window (1-7 days, default 3): opens a mediated thread with the Supplier; Admin can escalate/resolve and issue a dispute refund. Payouts can be held while a dispute is open.

---

## 2. Supplier

### 2.1 Onboarding
1. Register a supplier profile (business name, description, contact) → status `PENDING`.
2. Upload KYC documents; Admin reviews and approves/rejects.
3. Complete Stripe Connect onboarding (required before payouts).
4. Configure commercial settings: **shipping policy** (flat / free-over-threshold / per-item), **VAT** registration/number, and **fulfilment mode** (self-ship or platform-brokered delivery).

### 2.2 Catalogue and stock
- Create products (with a VAT rate) and variants (price, SKU, weight); schedule products to go live; manage images.
- Maintain stock: adjust levels, record lots with expiry; receive low-stock and expiry alerts.

### 2.3 Fulfilment and money
| Step | What happens |
|---|---|
| New sub-order | Supplier is notified on payment success; sees only their sub-order |
| Dispatch | Supplier marks the sub-order dispatched with a tracking reference. For platform delivery, this books the courier |
| Deliver | On delivery, the payout is triggered: `net = gross − commission` (commission on discounted goods only, never on shipping) transferred via Stripe Connect |
| Returns/disputes | Supplier approves/rejects returns and responds to disputes; an approved return or upheld dispute reverses the relevant payout share |

---

## 3. Admin

### 3.1 Operations
- **Supplier onboarding queue:** review KYC documents, approve/suspend/reject suppliers.
- **Catalogue oversight:** feature products, manage categories and homepage banners, suspend listings.
- **Orders:** view all orders and sub-orders, intervene in disputes.
- **Discounts:** create and manage discount codes (type, value, funding, caps, validity).

### 3.2 Refunds and payouts

![Returns and refund attribution](./diagrams/journey-returns-refund.png)

- **Process a return refund:** approve → refund the buyer the return's value → reverse the supplier's payout proportionally → restock.
- **Admin item refund** (`admin/{reference}/refund-items/`): select specific items of any order; the buyer is refunded those units' value and **each supplier's payout is reversed for the items they sold**. Not gated on delivery status; units restock.
- **Goodwill refund:** the amount-only admin refund refunds the buyer with no payout reversal (platform absorbs it).
- **Payouts:** view and process/hold payouts; reversals mark a payout `REVERSED`.
- Every privileged action is written to the `AuditLog`.

### 3.3 Analytics
- Dashboard KPIs: revenue by period/supplier/category, active orders, inventory and low-stock summary, dispute rate.

---

## 4. Cross-cutting states

**Sub-order:** `PENDING → CONFIRMED → DISPATCHED → DELIVERED`, or `→ CANCELLED`. The parent order status is derived from its sub-orders.
**Return:** `REQUESTED → APPROVED → REFUNDING → REFUNDED`, or `→ REJECTED`.
**Payout:** `PENDING → PROCESSING → PAID`, or `→ FAILED` / `→ REVERSED`.
**Courier delivery:** `QUOTED → BOOKED → EN_ROUTE → DELIVERED`, or `→ FAILED` / `→ CANCELLED`.
**Dispute:** `OPEN → RESPONDENT_REPLIED → ESCALATED → RESOLVING → RESOLVED`, or `→ REJECTED` / `→ CLOSED`.
