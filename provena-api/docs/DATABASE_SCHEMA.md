# Database Schema

**Product:** Provena
**Status:** Living document (reflects the models as of 2026-07)
**Source of truth:** the Django models under `provena-api/apps/*/models.py`. This document is a human-readable reference; regenerate it when models change.

> **Entity-relationship diagram:** the ER diagram is maintained in draw.io. Open the source with the drawio tooling (or `docs/diagrams/provena-erd.drawio`), export to `docs/diagrams/provena-erd.png`, and it renders below.
>
> ![Provena entity-relationship diagram](./diagrams/provena-erd.png)

---

## 1. Conventions

- **Primary keys.** User-facing resources use a UUID PK (`id`, `uuid4`) to prevent enumeration (ADR-005). A few internal one-to-one/child rows use an implicit integer PK.
- **Money.** All monetary values are `DecimalField` in GBP, quantised to pence (`decimal_places=2`); some legacy fields carry pence as integers (`*_amount_pence`). Never floats.
- **Timestamps.** Most tables carry `created_at` (`auto_now_add`) and `updated_at` (`auto_now`).
- **Enums.** Implemented as Django `TextChoices`; the stored value is the uppercase token shown below.
- **Deletion.** Financial and audit rows use `on_delete=PROTECT`; owned child rows use `CASCADE`; actor references that may outlive the actor use `SET_NULL`.

---

## 2. Models by app

### accounts

**User** (`AbstractBaseUser`)
| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| email | Email | unique; login identifier |
| first_name, last_name | Char | |
| role | Char(enum) | `BUYER` / `SUPPLIER` / `ADMIN` |
| is_active, is_staff | Bool | |
| totp_enabled | Bool | 2FA enrolled |
| totp_secret | Char | server-side TOTP seed |
| erased_at | DateTime? | set when the account is anonymised (ADR-011) |
| created_at, updated_at | DateTime | |

**AuditLog** - `actor` (FK User, SET_NULL), `action`, `target_type`, `target_id`, `metadata` (JSON), `created_at`. Append-only record of admin/privileged actions.
**Address** - `user` (FK), `label`, `full_name`, `line1/line2/city/postcode`, `country` (default `GB`), `is_default`.
**DataExportRequest** - `user` (FK), `status` (`PENDING`/…), `token_hash`, `payload` (JSON), `expires_at`, `requested_at`, `completed_at`. GDPR Article 20.
**PasswordResetToken** - `user` (FK), `token_hash` (unique), `expires_at`, `used_at`.

### suppliers

**Supplier**
| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user | O2O User | |
| business_name, slug | Char | slug unique |
| description, logo_url, website, phone | | |
| status | Char(enum) | `PENDING` / `APPROVED` / `SUSPENDED` / `REJECTED` |
| commission_rate | Decimal(5,2) | default 10.00; platform fee % (ADR-012) |
| vat_registered, vat_number | Bool / Char | |
| shipping_policy | Char(enum) | `FLAT` / `FREE_OVER_THRESHOLD` / `PER_ITEM` |
| shipping_flat_rate, shipping_per_item_rate | Decimal | |
| free_shipping_threshold | Decimal? | for `FREE_OVER_THRESHOLD` |
| fulfilment_mode | Char(enum) | `SUPPLIER_SHIP` (default) / `PLATFORM_DELIVERY` (ADR-013) |
| platform_delivery_fee | Decimal | flat fee when platform-delivered and no live quote |
| stripe_account_id, stripe_onboarding_complete | | Stripe Connect |

**SupplierAddress** - O2O Supplier; `line1/line2/city/county/postcode/country`.
**SupplierDocument** - FK Supplier; `document_type`, `file_url`, `status` (`PENDING`/`APPROVED`/`REJECTED`), `notes`, `reviewed_by` (FK User), `reviewed_at`. KYC.

### catalogue

**Category** - self-referential `parent` (SET_NULL) tree; `name`, `slug`, `image_url`, `position`, `is_active`, `dispute_window_days` (1-7, default 3).
**Product** - FK `supplier`, FK `category` (SET_NULL); `name`, `slug`, `description`, `status` (`DRAFT`/`ACTIVE`/`ARCHIVED`), **`vat_rate`** (`STANDARD` 20% / `REDUCED` 5% / `ZERO`), `is_featured`.
**ProductVariant** - FK `product`; `name`, `sku` (unique), `price`, `compare_at_price?`, `weight_grams`, `is_active`.
**ProductImage / VariantImage** - `url`, `alt_text`, `position`, `is_primary`.
**Banner** - homepage banner: `title`, `subtitle`, `image_url`, `link`, `is_active`, `position`.

### inventory

**StockLevel** - O2O `variant`; `quantity_available`, `quantity_reserved`, `low_stock_threshold`.
**StockLot** - FK `variant`; `lot_number`, `quantity_received`, `quantity_remaining`, `received_at`, `expires_at?`.
**StockMovement** - FK `variant`; `movement_type`, `quantity` (signed), `quantity_after`, `reference`, `performed_by` (FK User, SET_NULL). Audit trail.

### marketplace

**Cart** - O2O `buyer?` or `session_key?` (guest); check constraint requires one owner.
**CartItem** - FK `cart`, FK `variant`, `quantity`; unique per (cart, variant).
**CartReservation** - O2O `cart_item`, FK `variant`, `quantity`, `expires_at`. TTL stock hold.
**WishlistItem** - FK `buyer`, FK `variant`.
**Review** - FK `variant`, `reviewer` (FK User, SET_NULL); `rating` (1-5), `title`, `body`, `is_verified_purchase`, `is_approved`.

### orders

**Order**
| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| buyer | FK User (PROTECT) | |
| reference | Char | unique human reference (`ORD-…`) |
| status | Char(enum) | `PENDING`/`CONFIRMED`/`DISPATCHED`/`DELIVERED`/`CANCELLED` (derived from sub-orders) |
| shipping_* | Char | snapshot of the delivery address |
| goods_subtotal, discount_amount, shipping_amount, vat_amount, total_amount | Decimal | **pricing breakdown** (ADR-012) |
| discount_code, discount_funded_by | Char | snapshot of the applied code |

**SubOrder** - FK `order`, FK `supplier` (PROTECT); own `status`, the same **breakdown** columns plus `subtotal`, `fulfilment_mode` snapshot, `tracking_number`, `delivered_at`. One per supplier in an order.
**OrderItem** - FK `sub_order`, FK `variant` (PROTECT); snapshots `product_name`, `variant_name`, `sku`, `quantity`, `unit_price`, `vat_rate`, `vat_amount`. `returnable_quantity` derives from non-rejected returns.
**OrderReturn** - FK `sub_order`, `raised_by` (FK User, SET_NULL); `reason`, `status` (`REQUESTED`/`APPROVED`/`REFUNDING`/`REJECTED`/`REFUNDED`), `refund_amount`. A return with no items = full sub-order.
**ReturnItem** - FK `order_return`, FK `order_item` (PROTECT), `quantity`.
**DiscountCode** - `code` (unique), `discount_type` (`PERCENTAGE`/`FIXED`), `value`, `funded_by` (`PLATFORM`/`SUPPLIER`), `minimum_spend`, `valid_from/until?`, `max_uses?`, `max_uses_per_buyer?`, `is_active`.
**DiscountRedemption** - FK `code` (PROTECT), FK `buyer`, O2O `order`, `amount`. One row per order; enforces usage caps.

### payments

**Payment** - O2O `order` (PROTECT); `stripe_payment_intent_id` (unique), `stripe_client_secret`, `amount`, `currency` (`gbp`), `status` (`PENDING`/`SUCCEEDED`/`PARTIALLY_REFUNDED`/…), `refunded_amount`, `pending_refund_amount`.
**Payout** - O2O `sub_order` (PROTECT), FK `supplier`; `gross_amount`, `platform_fee`, `net_amount`, `status` (`PENDING`/`PROCESSING`/`PAID`/`FAILED`/`REVERSED`), `stripe_transfer_id`, `processing_started_at`.
**PaymentRefundRequest** - FK `payment`; `amount`, `stripe_idempotency_key` (unique), `stripe_refund_id`, `status`. Idempotency ledger so refund retries reuse one reservation.

### delivery

**CourierDelivery** - O2O `sub_order`; `provider`, `provider_quote_id`, `provider_delivery_id`, `fee_charged`, `courier_cost`, `currency` (`GBP`), `status` (`QUOTED`/`BOOKED`/`EN_ROUTE`/`DELIVERED`/`FAILED`/`CANCELLED`), `tracking_url`, `quote_expires_at`. Reconciliation ledger for platform-brokered delivery (ADR-013).

### disputes

**Dispute** - FK `sub_order` (PROTECT), `opened_by` / `respondent` (FK User); `dispute_type`, `description`, `resolution_requested`, `status` (`OPEN`/`RESPONDENT_REPLIED`/`ESCALATED`/`RESOLVING`/`RESOLVED`/`REJECTED`/`CLOSED`), `outcome`, `outcome_amount_pence?`, `response_deadline`, `payout_held`, `resolved_at?`.
**DisputeEvent** - append-only status/action log. **DisputeMessage** - threaded messages. **DisputeAttachment** - `filename`, `content_type`, `file_key`, `size_bytes`. **DisputeRefund** - FK `dispute` + `sub_order`; `stripe_refund_id` (unique), `amount_pence`, `status`.

### notifications

**Notification** - FK `recipient`; `notification_type`, `title`, `body`, `data` (JSON), `is_read`.
**NotificationPreference** - O2O `user`; per-event email toggles (`email_order_placed`, `email_order_dispatched`, `email_new_order`, `email_payout_received`).

---

## 3. Key relationships

- **User 1-1 Supplier**; a Supplier has many Products; a Product has many Variants; a Variant has one StockLevel and many StockLots/Movements.
- **Order 1-* SubOrder 1-* OrderItem.** A SubOrder belongs to exactly one Supplier; an OrderItem references a Variant. This is the fan-out that lets one checkout span multiple suppliers.
- **Payment 1-1 Order.** **Payout 1-1 SubOrder.** Money in is per order; money out is per sub-order (per supplier), which is why refunds reverse payouts per sub-order.
- **CourierDelivery 1-1 SubOrder** (only for `PLATFORM_DELIVERY` suppliers).
- **OrderReturn *-1 SubOrder**, **ReturnItem *-1 OrderItem** - returns and admin item refunds attribute value and payout reversal back to the selling supplier.
- **DiscountCode 1-* DiscountRedemption 1-1 Order** - a code is applied once per order; funding decides whether the platform or the supplier bears it.
- **Dispute *-1 SubOrder** with an append-only event/message log and optional DisputeRefund.

---

## 4. Money-path invariants (ADR-012)

- The order breakdown is computed once at checkout (`orders/pricing.py::compute_order_pricing`) and **snapshotted**; nothing downstream recomputes from live config.
- Per sub-order: `subtotal = goods_subtotal - discount_amount + shipping_amount`; VAT is *extracted* from the VAT-inclusive values (it does not add on top).
- Pro-rata splits (discount allocation, refund shares) use largest-remainder so parts sum to the whole exactly.
- Payout `net = gross - platform_fee`, fee on discounted goods only (never shipping); a refund reverses `net * (refund / sub_order.subtotal)`.
