export type SupplierStatus = 'APPROVED' | 'PENDING' | 'REJECTED' | 'SUSPENDED'
export type UserRole = 'BUYER' | 'SUPPLIER' | 'ADMIN'
export type PlatformOrderStatus = 'PENDING' | 'CONFIRMED' | 'DISPATCHED' | 'DELIVERED' | 'CANCELLED'
export type PayoutStatus = 'PENDING' | 'PROCESSING' | 'PAID' | 'FAILED'

export const PLATFORM_STATS = {
  revenue_30d:         '1 284.50',
  revenue_prev_30d:    '1 053.20',
  orders_30d:          94,
  orders_prev_30d:     81,
  active_users:        234,
  active_users_prev:   198,
  pending_suppliers:   3,
}

// ── Suppliers ─────────────────────────────────────────────────────────────────

export interface AdminSupplier {
  id: string
  business_name: string
  slug: string
  location: string
  email: string
  status: SupplierStatus
  rating: number | null
  product_count: number
  order_count: number
  joined_at: string
}

export const ADMIN_SUPPLIERS: AdminSupplier[] = [
  { id: 's1', business_name: 'Fresh Farms',        slug: 'fresh-farms',        location: 'Somerset, England',     email: 'hello@freshfarms.co.uk',       status: 'APPROVED',  rating: 4.8, product_count: 4,  order_count: 38, joined_at: '2026-01-15T10:00:00Z' },
  { id: 's2', business_name: 'Green Valley Dairy',  slug: 'green-valley-dairy', location: 'Yorkshire, UK',         email: 'info@greenvalleydairy.co.uk',  status: 'APPROVED',  rating: 4.6, product_count: 3,  order_count: 27, joined_at: '2026-02-03T09:30:00Z' },
  { id: 's3', business_name: 'Grain & Co.',          slug: 'grain-and-co',       location: 'Norfolk, UK',           email: 'hello@grainandco.co.uk',       status: 'APPROVED',  rating: 4.8, product_count: 3,  order_count: 22, joined_at: '2026-02-10T11:00:00Z' },
  { id: 's4', business_name: 'Wild Root Pantry',    slug: 'wild-root-pantry',   location: 'Devon, England',        email: 'contact@wildrootpantry.co.uk', status: 'APPROVED',  rating: 4.7, product_count: 3,  order_count: 19, joined_at: '2026-03-01T08:00:00Z' },
  { id: 's5', business_name: 'Lakeland Butchery',   slug: 'lakeland-butchery',  location: 'Cumbria, England',      email: 'orders@lakelandbutchery.co.uk',status: 'PENDING',   rating: null, product_count: 0, order_count: 0,  joined_at: '2026-06-28T14:22:00Z' },
  { id: 's6', business_name: 'Devon Sea Salt Co.',  slug: 'devon-sea-salt',     location: 'Devon, England',        email: 'sea@devonseasalt.co.uk',       status: 'PENDING',   rating: null, product_count: 0, order_count: 0,  joined_at: '2026-06-29T10:15:00Z' },
  { id: 's7', business_name: 'The Orchard Press',   slug: 'orchard-press',      location: 'Herefordshire, England',email: 'press@theorchardpress.co.uk',  status: 'PENDING',   rating: null, product_count: 0, order_count: 0,  joined_at: '2026-06-30T08:40:00Z' },
  { id: 's8', business_name: 'Highland Honey Co.',  slug: 'highland-honey',     location: 'Perthshire, Scotland',  email: 'buzz@highlandhoney.scot',      status: 'REJECTED',  rating: null, product_count: 0, order_count: 0,  joined_at: '2026-05-10T09:00:00Z' },
]

// ── Users ─────────────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string
  name: string
  email: string
  role: UserRole
  is_active: boolean
  joined_at: string
  last_active_at: string
}

export const ADMIN_USERS: AdminUser[] = [
  { id: 'u1',  name: 'James Thorpe',    email: 'j.thorpe@gmail.com',     role: 'BUYER',    is_active: true,  joined_at: '2026-01-20T10:00:00Z', last_active_at: '2026-06-30T12:00:00Z' },
  { id: 'u2',  name: 'Amara Boateng',   email: 'amara.b@outlook.com',    role: 'BUYER',    is_active: true,  joined_at: '2026-02-05T09:00:00Z', last_active_at: '2026-06-29T18:30:00Z' },
  { id: 'u3',  name: 'Sofia Marchetti', email: 'sofia.m@icloud.com',     role: 'BUYER',    is_active: true,  joined_at: '2026-02-14T11:00:00Z', last_active_at: '2026-06-28T14:00:00Z' },
  { id: 'u4',  name: 'Kwame Osei',      email: 'kwame.o@gmail.com',      role: 'BUYER',    is_active: true,  joined_at: '2026-03-02T08:00:00Z', last_active_at: '2026-06-27T20:00:00Z' },
  { id: 'u5',  name: 'Rachel Chen',     email: 'r.chen@gmail.com',       role: 'BUYER',    is_active: true,  joined_at: '2026-03-10T16:00:00Z', last_active_at: '2026-06-30T15:48:00Z' },
  { id: 'u6',  name: 'Theo Parker',     email: 'theo.p@hotmail.com',     role: 'BUYER',    is_active: false, joined_at: '2026-04-01T09:00:00Z', last_active_at: '2026-05-12T10:00:00Z' },
  { id: 'u7',  name: 'Fresh Farms',     email: 'hello@freshfarms.co.uk', role: 'SUPPLIER', is_active: true,  joined_at: '2026-01-15T10:00:00Z', last_active_at: '2026-06-30T09:12:00Z' },
  { id: 'u8',  name: 'Green Valley Dairy', email: 'info@greenvalleydairy.co.uk', role: 'SUPPLIER', is_active: true, joined_at: '2026-02-03T09:30:00Z', last_active_at: '2026-06-29T14:00:00Z' },
  { id: 'u9',  name: 'Grain & Co.',     email: 'hello@grainandco.co.uk', role: 'SUPPLIER', is_active: true,  joined_at: '2026-02-10T11:00:00Z', last_active_at: '2026-06-28T11:00:00Z' },
  { id: 'u10', name: 'Wild Root Pantry',email: 'contact@wildrootpantry.co.uk', role: 'SUPPLIER', is_active: true, joined_at: '2026-03-01T08:00:00Z', last_active_at: '2026-06-27T16:00:00Z' },
  { id: 'u11', name: 'Platform Admin',  email: 'admin@provena.co.uk',    role: 'ADMIN',    is_active: true,  joined_at: '2026-01-01T00:00:00Z', last_active_at: '2026-06-30T16:00:00Z' },
]

// ── Platform orders ───────────────────────────────────────────────────────────

export interface PlatformOrder {
  id: string
  reference: string
  buyer_name: string
  supplier_names: string[]
  total: string
  status: PlatformOrderStatus
  created_at: string
}

export const PLATFORM_ORDERS: PlatformOrder[] = [
  { id: 'ord1', reference: 'ORD-2026-0094', buyer_name: 'Rachel Chen',    supplier_names: ['Fresh Farms'],                          total: '12.50', status: 'PENDING',    created_at: '2026-06-30T15:48:00Z' },
  { id: 'ord2', reference: 'ORD-2026-0093', buyer_name: 'James Thorpe',   supplier_names: ['Fresh Farms'],                          total: '11.10', status: 'CONFIRMED',  created_at: '2026-06-30T09:12:00Z' },
  { id: 'ord3', reference: 'ORD-2026-0092', buyer_name: 'Amara Boateng',  supplier_names: ['Fresh Farms', 'Wild Root Pantry'],       total: '21.40', status: 'DISPATCHED', created_at: '2026-06-29T14:35:00Z' },
  { id: 'ord4', reference: 'ORD-2026-0091', buyer_name: 'Sofia Marchetti',supplier_names: ['Green Valley Dairy'],                    total: '9.20',  status: 'DELIVERED',  created_at: '2026-06-28T11:05:00Z' },
  { id: 'ord5', reference: 'ORD-2026-0090', buyer_name: 'Kwame Osei',     supplier_names: ['Fresh Farms', 'Grain & Co.'],            total: '17.80', status: 'DELIVERED',  created_at: '2026-06-27T08:20:00Z' },
  { id: 'ord6', reference: 'ORD-2026-0089', buyer_name: 'Theo Parker',    supplier_names: ['Wild Root Pantry'],                      total: '8.50',  status: 'CANCELLED',  created_at: '2026-06-26T16:30:00Z' },
  { id: 'ord7', reference: 'ORD-2026-0088', buyer_name: 'Rachel Chen',    supplier_names: ['Grain & Co.', 'Green Valley Dairy'],     total: '14.30', status: 'DELIVERED',  created_at: '2026-06-26T10:00:00Z' },
]

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface DayRevenue {
  date: string      // 'Jun 17'
  revenue: number
  orders: number
}

export const REVENUE_BY_DAY: DayRevenue[] = [
  { date: 'Jun 17', revenue: 78.4,  orders: 6 },
  { date: 'Jun 18', revenue: 94.2,  orders: 8 },
  { date: 'Jun 19', revenue: 61.0,  orders: 5 },
  { date: 'Jun 20', revenue: 112.8, orders: 9 },
  { date: 'Jun 21', revenue: 88.5,  orders: 7 },
  { date: 'Jun 22', revenue: 134.0, orders: 11 },
  { date: 'Jun 23', revenue: 105.6, orders: 9 },
  { date: 'Jun 24', revenue: 72.3,  orders: 6 },
  { date: 'Jun 25', revenue: 98.0,  orders: 8 },
  { date: 'Jun 26', revenue: 117.4, orders: 10 },
  { date: 'Jun 27', revenue: 89.1,  orders: 7 },
  { date: 'Jun 28', revenue: 142.0, orders: 12 },
  { date: 'Jun 29', revenue: 88.7,  orders: 8 },
  { date: 'Jun 30', revenue: 103.5, orders: 9 },
]

export interface TopProduct {
  sku: string
  name: string
  supplier: string
  units_sold: number
  revenue: string
}

export const TOP_PRODUCTS: TopProduct[] = [
  { sku: 'HNYWF-340', name: 'Raw Wildflower Honey',    supplier: 'Wild Root Pantry',  units_sold: 89, revenue: '756.50' },
  { sku: 'CHDR-400G', name: 'Farmhouse Cheddar',       supplier: 'Green Valley Dairy',units_sold: 74, revenue: '310.80' },
  { sku: 'CARR-1KG',  name: 'Carrots',                 supplier: 'Fresh Farms',       units_sold: 120, revenue: '300.00' },
  { sku: 'FLOUR-1KG', name: 'Sourdough Flour',         supplier: 'Grain & Co.',       units_sold: 68, revenue: '217.60' },
  { sku: 'ACV-500',   name: 'Apple Cider Vinegar',     supplier: 'Wild Root Pantry',  units_sold: 41, revenue: '213.20' },
]

export interface SupplierPerf {
  name: string
  revenue: string
  orders: number
  avg_order: string
  payout_pending: string
}

export const SUPPLIER_PERFORMANCE: SupplierPerf[] = [
  { name: 'Fresh Farms',        revenue: '428.50', orders: 38, avg_order: '11.28', payout_pending: '198.40' },
  { name: 'Wild Root Pantry',   revenue: '312.80', orders: 27, avg_order: '11.59', payout_pending: '156.30' },
  { name: 'Green Valley Dairy', revenue: '248.40', orders: 22, avg_order: '11.29', payout_pending: '115.20' },
  { name: 'Grain & Co.',        revenue: '197.60', orders: 19, avg_order: '10.40', payout_pending: '89.50' },
]

// ── Payouts ───────────────────────────────────────────────────────────────────

export interface PlatformPayout {
  id: string
  reference: string
  supplier_name: string
  order_reference: string
  gross_amount: string
  platform_fee: string
  net_amount: string
  status: PayoutStatus
  created_at: string
}

export const PLATFORM_PAYOUTS: PlatformPayout[] = [
  { id: 'py1', reference: 'PAY-FF-0041',  supplier_name: 'Fresh Farms',        order_reference: 'ORD-2026-0093', gross_amount: '11.10', platform_fee: '1.11', net_amount: '9.99',  status: 'PENDING',    created_at: '2026-06-30T09:12:00Z' },
  { id: 'py2', reference: 'PAY-WRP-0021', supplier_name: 'Wild Root Pantry',   order_reference: 'ORD-2026-0092', gross_amount: '8.50',  platform_fee: '0.85', net_amount: '7.65',  status: 'PENDING',    created_at: '2026-06-29T14:35:00Z' },
  { id: 'py3', reference: 'PAY-FF-0040',  supplier_name: 'Fresh Farms',        order_reference: 'ORD-2026-0092', gross_amount: '12.40', platform_fee: '1.24', net_amount: '11.16', status: 'PROCESSING', created_at: '2026-06-29T14:35:00Z' },
  { id: 'py4', reference: 'PAY-GVD-0018', supplier_name: 'Green Valley Dairy', order_reference: 'ORD-2026-0091', gross_amount: '9.20',  platform_fee: '0.92', net_amount: '8.28',  status: 'PROCESSING', created_at: '2026-06-28T11:05:00Z' },
  { id: 'py5', reference: 'PAY-FF-0039',  supplier_name: 'Fresh Farms',        order_reference: 'ORD-2026-0090', gross_amount: '11.80', platform_fee: '1.18', net_amount: '10.62', status: 'PAID',       created_at: '2026-06-27T08:20:00Z' },
  { id: 'py6', reference: 'PAY-GC-0015',  supplier_name: 'Grain & Co.',        order_reference: 'ORD-2026-0090', gross_amount: '6.00',  platform_fee: '0.60', net_amount: '5.40',  status: 'PAID',       created_at: '2026-06-27T08:20:00Z' },
]

export function trend(current: number, previous: number): number {
  if (previous === 0) return 0
  return Math.round(((current - previous) / previous) * 1000) / 10
}
