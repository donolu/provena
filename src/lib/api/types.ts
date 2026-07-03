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
  refresh: string
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
  added_at: string
  updated_at: string
}

export interface Cart {
  id: string
  items: CartItem[]
  total: string
  item_count: number
  updated_at: string
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
  status: OrderStatus
  subtotal: string
  tracking_number: string
  items: OrderItem[]
  created_at: string
  updated_at: string
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

export interface SupplierProfile {
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

// ── Payments ──────────────────────────────────────────────────────────────────

export type PayoutStatus = 'PENDING' | 'PROCESSING' | 'PAID' | 'FAILED'

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
