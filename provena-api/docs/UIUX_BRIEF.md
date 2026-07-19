# UI/UX Brief

**Product:** Provena
**Status:** Living document (2026-07)
**Scope:** the Next.js storefront and role dashboards (`provena-web`). Native apps are out of scope for v1.

> Navigation map / sitemap is maintained in draw.io; export to `docs/diagrams/sitemap.png`.
>
> ![Provena sitemap](./diagrams/sitemap.png)

---

## 1. Design principles

1. **Fresh, editorial, trustworthy.** Provena sells fresh produce; the interface should feel like a considered greengrocer, not a discount warehouse. Generous whitespace, a serif display face, calm greens.
2. **The price you see is the price you pay.** Every step of checkout shows the same running total (goods, discount, shipping, VAT, total). No surprises at the Pay button.
3. **Show provenance.** Product and supplier pages foreground origin, the supplier, and freshness.
4. **One clear action per screen.** Especially in checkout and fulfilment flows, the primary action is unambiguous and never competes with secondary links.
5. **Accessible by default.** WCAG 2.1 AA is a requirement (see §6), not a polish pass.

---

## 2. Brand and visual language

### 2.1 Colour palette (Tailwind theme)

| Token | Hex | Use |
|---|---|---|
| `mist` | `#F4F7F4` | App background, subtle surfaces |
| `forest` | `#1B2B1E` | Primary text, primary buttons, headers |
| `meadow` | `#4C8B6B` | Accent, success, hover on primary |
| `marigold` | `#E8B84B` | Highlights, badges, promotional accents |
| `hoarfrost` | `#CDD5CE` | Borders, dividers, muted lines |
| `soil` | `#7C6E5B` | Secondary/muted text, labels |
| `terracotta` | (alert accent) | Errors, destructive actions, validation messages |

Greens carry the brand; marigold is the sparing highlight; terracotta is reserved for errors and destructive actions. Keep contrast within AA (see §6).

### 2.2 Typography

| Family | Role |
|---|---|
| **Fraunces** (serif, `font-display`) | Page and section headings; editorial voice |
| **Plus Jakarta Sans** (`font-sans`) | Body, UI labels, forms, buttons |
| **DM Mono** (`font-mono`) | Prices, order references, SKUs, any figure that should align |

Money and identifiers always render in the mono face so columns of figures align and references are unambiguous. Labels use small uppercase tracking for a tidy, structured feel.

### 2.3 Tone of voice

British English throughout. Plain, warm, direct. Errors are specific and actionable ("Enter a valid postcode", not "Invalid input"). No dark patterns; no fake urgency.

---

## 3. Layout and components

- **Grid:** responsive, max content width with comfortable gutters; card-based product grids that reflow from 4 columns (desktop) to 1 (mobile).
- **Surfaces:** white cards on `mist`, `hoarfrost` borders, small radii, minimal shadow.
- **Buttons:** primary = `forest` fill / `mist` text, hover `meadow`; secondary = outline; destructive = `terracotta`. Disabled state at reduced opacity with a not-allowed cursor.
- **Forms:** labelled inputs (small uppercase label), inline validation, `forest` focus ring. React Hook Form + Zod validation mirrors the API's rules.
- **Order breakdown** (`OrderBreakdown`): the reusable component that renders goods / discount / shipping / VAT / total, used on checkout, the payment step, and order detail so the figures are always presented identically.
- **Status pills:** one consistent pill style mapped to each state machine (sub-order, return, payout, courier, dispute) with a colour per state.
- **Feedback states:** every data view defines loading (skeleton), empty (illustration + one clear next action), and error (terracotta message + retry).

---

## 4. Key screens

### 4.1 Buyer
- **Storefront home:** hero banner (admin-curated), featured categories/products, search entry.
- **Category / search results:** filter rail (category, price, supplier, availability), product grid, sort.
- **Product detail:** gallery, variant selector, price (mono), VAT-inclusive note, supplier card, reviews, related products, add-to-cart.
- **Cart:** line items with reservation countdown, running subtotal, "excl. shipping & VAT" note, checkout CTA.
- **Checkout:** address → discount code (with live preview) → order breakdown → Stripe payment element → Pay `£total`.
- **Orders / order detail:** live sub-order statuses, courier tracking link, cancel/return/dispute actions, full breakdown.
- **Account:** profile, addresses, 2FA, notification preferences, data export / erasure.

### 4.2 Supplier dashboard
- **Overview:** performance stats (sales, fulfilment time, return rate), new-order alerts.
- **Catalogue & inventory:** product/variant CRUD, stock levels, lots/expiry, low-stock flags.
- **Sub-orders:** queue with dispatch (tracking) and deliver actions; returns to approve/reject.
- **Settings:** shipping policy, VAT number, fulfilment mode, Stripe Connect status.
- **Payouts:** payout history and statuses.

### 4.3 Admin console
- **Dashboard:** revenue/orders/users KPIs, dispute rate, inventory summary.
- **Supplier onboarding:** KYC queue with document review, approve/suspend/reject.
- **Orders & refunds:** all orders; **item-level refund** picker (select items → refund attributed to the selling supplier); goodwill refund; payout process/hold.
- **Discounts:** code management (type, value, funding, caps, validity).
- **Content:** banners, featured products, categories.
- **Audit log:** searchable record of privileged actions.

---

## 5. Interaction patterns

- **Real-time order status** via WebSocket; the UI updates sub-order pills without a refresh.
- **Optimistic-but-safe money actions:** refunds/cancellations confirm in a dialog stating the amount and who bears it before calling the API.
- **Cart reservation countdown** communicates the 30-minute hold so buyers understand availability.
- **Discount preview** is advisory and never blocks; the authoritative validation happens at checkout.

---

## 6. Accessibility (WCAG 2.1 AA)

- Colour contrast ≥ 4.5:1 for body text, ≥ 3:1 for large text and UI boundaries; never rely on colour alone (pills carry a label, not just a hue).
- Full keyboard operability; visible focus rings (`forest`); logical tab order; skip-to-content link.
- Semantic landmarks and headings; form inputs have associated labels and `aria-describedby` for errors; live regions announce async status and validation.
- Respect `prefers-reduced-motion`; no motion-only feedback.
- Target sizes and spacing comfortable on touch; responsive down to small mobile without horizontal scroll.

---

## 7. Responsive and performance

- Mobile-first; product grids and dashboards reflow to single column; tables become stacked cards on small screens.
- SSR for SEO-sensitive pages (storefront, product, category); client rendering for authenticated dashboards.
- Images lazy-loaded with intrinsic sizing; skeletons prevent layout shift.
