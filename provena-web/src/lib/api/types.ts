// ── Auth ──────────────────────────────────────────────────────────────────────

export type UserRole = 'BUYER' | 'SUPPLIER' | 'ADMIN'

export interface UserProfile {
  id: string
  email: string
  first_name: string
  last_name: string
  role: UserRole
  totp_enabled: boolean
  created_at: string
}

export interface LoginResponse {
  access: string
  user: UserProfile
}

export interface TOTPLoginRequired {
  totp_session_token: string
}

// ── Catalogue ─────────────────────────────────────────────────────────────────

export interface Category {
  id: string
  name: string
  slug: string
  description: string
  image_url: string | null
  parent_slug: string | null
  children: Category[]
  position: number
  is_active: boolean
  product_count: number
}

export interface ProductVariant {
  id: string
  name: string
  sku: string
  price: string
  compare_at_price: string | null
  weight_grams: number
  is_active: boolean
  on_sale: boolean
  discount_percent: string | null
}

export interface ProductImage {
  id: string
  url: string
  alt_text: string
  position: number
  is_primary: boolean
}

export type ProductStatus = 'ACTIVE' | 'DRAFT' | 'ARCHIVED'

export interface Product {
  id: string
  name: string
  slug: string
  description: string
  status: ProductStatus
  is_featured: boolean
  supplier_slug: string
  supplier_name: string
  category_slug: string | null
  category_name: string | null
  variants: ProductVariant[]
  images: ProductImage[]
  average_rating: number | null
  review_count: number
  created_at: string
  updated_at: string
}

export interface Review {
  id: string
  variant: string
  variant_sku: string
  reviewer_email: string | null
  rating: number
  title: string
  body: string
  is_verified_purchase: boolean
  is_approved: boolean
  created_at: string
  updated_at: string
}

// ── Paginated response ────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ── Marketplace / Cart ────────────────────────────────────────────────────────

export interface CartItem {
  id: string
  variant: string
  variant_sku: string
  variant_name: string
  product_name: string
  price: string
  quantity: number
  subtotal: string
  reservation_expires_at: string | null
  added_at: string
  updated_at: string
}

export interface Cart {
  id: string | null
  items: CartItem[]
  total: string
  item_count: number
  updated_at?: string
}

export interface WishlistItem {
  id: string
  variant: string
  variant_sku: string
  variant_name: string
  product_name: string
  price: string
  is_active: boolean
  added_at: string
}

// ── Orders ────────────────────────────────────────────────────────────────────

export type OrderStatus = 'PENDING' | 'CONFIRMED' | 'DISPATCHED' | 'DELIVERED' | 'CANCELLED'
export type DisputeStatus =
  | 'OPEN'
  | 'RESPONDENT_REPLIED'
  | 'ESCALATED'
  | 'RESOLVING'
  | 'RESOLVED'
  | 'REJECTED'
  | 'CLOSED'
export type ReturnStatus = 'REQUESTED' | 'APPROVED' | 'REFUNDING' | 'REJECTED' | 'REFUNDED'

export interface ReturnItem {
  id: string
  order_item_id: string
  sku: string
  product_name: string
  quantity: number
}

export interface OrderReturn {
  id: string
  sub_order_id: string
  order_reference: string
  supplier_name: string
  reason: string
  status: ReturnStatus
  supplier_notes: string
  refund_amount: string | null
  items: ReturnItem[]
  raised_by_email: string | null
  created_at: string
  updated_at: string
}

export interface OrderDispute {
  id: string
  sub_order_id: string
  reason: string
  status: DisputeStatus
  resolution: string
  raised_by_email: string | null
  created_at: string
  updated_at: string
}

export interface OrderItem {
  id: string
  product_name: string
  variant_name: string
  sku: string
  quantity: number
  unit_price: string
  total_price: string
}

export interface SubOrder {
  id: string
  supplier_name: string
  supplier_slug: string
  supplier_vat_number: string
  status: OrderStatus
  goods_subtotal: string
  discount_amount: string
  shipping_amount: string
  vat_amount: string
  subtotal: string
  fulfilment_mode: FulfilmentMode
  tracking_number: string
  delivered_at: string | null
  courier: CourierDelivery | null
  items: OrderItem[]
  disputes: OrderDispute[]
  returns: OrderReturn[]
  created_at: string
  updated_at: string
}

export type CourierStatus =
  | 'QUOTED'
  | 'BOOKED'
  | 'EN_ROUTE'
  | 'DELIVERED'
  | 'FAILED'
  | 'CANCELLED'

export interface CourierDelivery {
  status: CourierStatus
  tracking_url: string
}

export interface SubOrderListItem {
  id: string
  order_reference: string
  buyer_email: string
  supplier_name: string
  status: OrderStatus
  subtotal: string
  tracking_number: string
  created_at: string
}

export interface Order {
  id: string
  reference: string
  status: OrderStatus
  buyer_email: string
  shipping_name: string
  shipping_line1: string
  shipping_line2: string
  shipping_city: string
  shipping_postcode: string
  shipping_country: string
  goods_subtotal: string
  discount_amount: string
  discount_code: string
  shipping_amount: string
  vat_amount: string
  total_amount: string
  notes: string
  payment_id: string | null
  payment_status: string | null
  refunded_amount: string | null
  sub_orders: SubOrder[]
  created_at: string
  updated_at: string
}

// ── Suppliers ─────────────────────────────────────────────────────────────────

export type SupplierStatus = 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'REJECTED'

export type ShippingPolicy = 'FLAT' | 'FREE_OVER_THRESHOLD' | 'PER_ITEM'

export type FulfilmentMode = 'SUPPLIER_SHIP' | 'PLATFORM_DELIVERY'

export interface SupplierShipping {
  fulfilment_mode: FulfilmentMode
  platform_delivery_fee: string
  shipping_policy: ShippingPolicy
  shipping_flat_rate: string
  shipping_per_item_rate: string
  free_shipping_threshold: string | null
}

export interface SupplierAddress {
  line1: string
  line2: string
  city: string
  county: string
  postcode: string
  country: string
}

export type DocumentStatus = 'PENDING' | 'APPROVED' | 'REJECTED'

export interface SupplierDocument {
  id: string
  document_type: string
  file_url: string
  status: DocumentStatus
  notes: string
  uploaded_at: string
  reviewed_at: string | null
  reviewed_by_email: string | null
}

export interface PublicSupplier extends SupplierShipping {
  id: string
  business_name: string
  slug: string
  description: string
  logo_url: string
  website: string
  address: SupplierAddress | null
  average_rating: number | null
  product_count: number
}

export interface SupplierProfile extends SupplierShipping {
  id: string
  user_email: string
  business_name: string
  slug: string
  description: string
  logo_url: string
  website: string
  phone: string
  status: SupplierStatus
  commission_rate: string
  vat_registered: boolean
  vat_number: string
  stripe_onboarding_complete: boolean
  address: SupplierAddress | null
  documents: SupplierDocument[]
  created_at: string
}

export interface AdminSupplier extends SupplierProfile {
  stripe_account_id: string | null
  updated_at: string
}

// ── Admin Users ───────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string
  email: string
  first_name: string
  last_name: string
  role: UserRole
  is_active: boolean
  is_staff: boolean
  totp_enabled: boolean
  created_at: string
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface SalesSummary {
  total_revenue: string
  total_orders: number
  avg_order_value: string
  from_date: string
  to_date: string
}

export interface RevenueDataPoint {
  period: string
  revenue: string
  order_count: number
}

export interface TopProduct {
  product_name: string
  supplier_name?: string
  variant_sku?: string
  units_sold: number
  revenue: string
}

export interface SupplierPerformanceStat {
  supplier_name: string
  total_revenue: string
  sub_order_count: number
  pending_payout: string
}

export interface SupplierOwnSummary {
  total_revenue: string
  total_orders: number
  pending_orders: number
  avg_order_value: string
}

// ── Audit log ─────────────────────────────────────────────────────────────────

export interface AuditLog {
  id: string
  actor_email: string | null
  action: string
  target_type: string
  target_id: string
  metadata: Record<string, unknown>
  created_at: string
}

// ── Inventory ─────────────────────────────────────────────────────────────────

export interface StockLevel {
  id: string
  variant_sku: string
  product_name: string
  quantity_available: number
  quantity_reserved: number
  quantity_on_hand: number
  low_stock_threshold: number
  is_low_stock: boolean
  updated_at: string
}

export interface StockLot {
  id: string
  lot_number: string
  quantity_received: number
  quantity_remaining: number
  received_at: string
  expires_at: string | null
  notes: string
}

export interface StockMovement {
  id: string
  movement_type: string
  movement_type_display: string
  quantity: number
  quantity_after: number
  reference: string
  notes: string
  performed_by_email: string | null
  created_at: string
}

// ── Payments ──────────────────────────────────────────────────────────────────

export type PayoutStatus = 'PENDING' | 'PROCESSING' | 'PAID' | 'FAILED' | 'REVERSED'

export type DiscountType = 'PERCENTAGE' | 'FIXED'
export type DiscountFunding = 'PLATFORM' | 'SUPPLIER'

export interface DiscountCode {
  id: string
  code: string
  discount_type: DiscountType
  value: string
  funded_by: DiscountFunding
  minimum_spend: string
  valid_from: string | null
  valid_until: string | null
  max_uses: number | null
  max_uses_per_buyer: number | null
  is_active: boolean
  times_used: number
  created_at: string
  updated_at: string
}

export interface DiscountValidateResult {
  valid: boolean
  code?: string
  discount_amount?: string
  new_total?: string
  reason?: string
}

export interface Payout {
  id: string
  sub_order_id: string
  order_reference: string
  supplier_name: string
  gross_amount: string
  platform_fee: string
  net_amount: string
  status: PayoutStatus
  status_display: string
  stripe_transfer_id: string | null
  created_at: string
  updated_at: string
}

export interface Payment {
  id: string
  order_reference: string
  amount: string
  currency: string
  status: string
  status_display: string
  stripe_payment_intent_id: string
  refunded_amount: string | null
  created_at: string
  updated_at: string
}

export interface NotificationPreferences {
  email_order_placed: boolean
  email_order_dispatched: boolean
  email_new_order: boolean
  email_payout_received: boolean
  updated_at: string
}

// ── Notifications ─────────────────────────────────────────────────────────────

export type NotificationType =
  | 'LOW_STOCK'
  | 'ORDER_PLACED'
  | 'ORDER_DISPATCHED'
  | 'ORDER_DELIVERED'
  | 'PAYMENT_SUCCEEDED'
  | 'GENERAL'

export interface Notification {
  id: string
  notification_type: NotificationType
  title: string
  body: string
  data: Record<string, unknown>
  is_read: boolean
  created_at: string
}

// ── Banners ───────────────────────────────────────────────────────────────────

export interface Banner {
  id: string
  title: string
  subtitle: string
  image_url: string
  link: string
  is_active: boolean
  position: number
  created_at: string
  updated_at: string
}
