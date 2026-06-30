// Mock data scoped to the authenticated supplier (Fresh Farms).
// Replace with real API calls once auth is wired.

export const CURRENT_SUPPLIER = {
  id: 's1',
  business_name: 'Fresh Farms',
  slug: 'fresh-farms',
  location: 'Somerset, England',
  rating: 4.8,
  initials: 'FF',
}

export const SUPPLIER_STATS = {
  revenue_30d: '284.50',
  revenue_prev_30d: '253.20',
  orders_30d: 23,
  orders_prev_30d: 20,
  pending_payout: '198.40',
  low_stock_count: 1,
}

export type OrderStatus = 'PENDING' | 'CONFIRMED' | 'DISPATCHED' | 'DELIVERED' | 'CANCELLED'
export type PayoutStatus = 'PENDING' | 'PROCESSING' | 'PAID' | 'FAILED'

export interface SubOrderItem {
  product_name: string
  variant_name: string
  sku: string
  quantity: number
  unit_price: string
}

export interface SubOrder {
  id: string
  reference: string
  buyer_name: string
  items: SubOrderItem[]
  subtotal: string
  status: OrderStatus
  created_at: string
}

export interface SupplierPayout {
  id: string
  reference: string
  order_reference: string
  gross_amount: string
  platform_fee: string
  net_amount: string
  status: PayoutStatus
  created_at: string
  paid_at?: string
}

export const SUB_ORDERS: SubOrder[] = [
  {
    id: 'so1',
    reference: 'FF-2026-0041',
    buyer_name: 'James T.',
    items: [
      { product_name: 'Carrots', variant_name: '1 kg', sku: 'CARR-1KG', quantity: 3, unit_price: '2.50' },
      { product_name: 'Spinach', variant_name: '200 g', sku: 'SPIN-200G', quantity: 2, unit_price: '1.80' },
    ],
    subtotal: '11.10',
    status: 'CONFIRMED',
    created_at: '2026-06-30T09:12:00Z',
  },
  {
    id: 'so2',
    reference: 'FF-2026-0040',
    buyer_name: 'Amara B.',
    items: [
      { product_name: 'Tenderstem Broccoli', variant_name: '250 g', sku: 'BRCL-250G', quantity: 1, unit_price: '2.40' },
      { product_name: 'Carrots', variant_name: '1 kg', sku: 'CARR-1KG', quantity: 4, unit_price: '2.50' },
    ],
    subtotal: '12.40',
    status: 'DISPATCHED',
    created_at: '2026-06-29T14:35:00Z',
  },
  {
    id: 'so3',
    reference: 'FF-2026-0039',
    buyer_name: 'Sofia M.',
    items: [
      { product_name: 'Spinach', variant_name: '200 g', sku: 'SPIN-200G', quantity: 4, unit_price: '1.80' },
    ],
    subtotal: '7.20',
    status: 'DELIVERED',
    created_at: '2026-06-28T11:05:00Z',
  },
  {
    id: 'so4',
    reference: 'FF-2026-0038',
    buyer_name: 'Kwame O.',
    items: [
      { product_name: 'Carrots', variant_name: '1 kg', sku: 'CARR-1KG', quantity: 2, unit_price: '2.50' },
      { product_name: 'Tenderstem Broccoli', variant_name: '250 g', sku: 'BRCL-250G', quantity: 2, unit_price: '2.40' },
      { product_name: 'Spinach', variant_name: '200 g', sku: 'SPIN-200G', quantity: 1, unit_price: '1.80' },
    ],
    subtotal: '11.80',
    status: 'DELIVERED',
    created_at: '2026-06-27T08:20:00Z',
  },
  {
    id: 'so5',
    reference: 'FF-2026-0037',
    buyer_name: 'Rachel C.',
    items: [
      { product_name: 'Carrots', variant_name: '1 kg', sku: 'CARR-1KG', quantity: 5, unit_price: '2.50' },
    ],
    subtotal: '12.50',
    status: 'PENDING',
    created_at: '2026-06-30T15:48:00Z',
  },
  {
    id: 'so6',
    reference: 'FF-2026-0036',
    buyer_name: 'Theo P.',
    items: [
      { product_name: 'Spinach', variant_name: '200 g', sku: 'SPIN-200G', quantity: 2, unit_price: '1.80' },
    ],
    subtotal: '3.60',
    status: 'CANCELLED',
    created_at: '2026-06-26T16:30:00Z',
  },
]

export const PAYOUTS: SupplierPayout[] = [
  {
    id: 'py1',
    reference: 'PAY-FF-0039',
    order_reference: 'FF-2026-0039',
    gross_amount: '7.20',
    platform_fee: '0.72',
    net_amount: '6.48',
    status: 'PAID',
    created_at: '2026-06-28T11:05:00Z',
    paid_at: '2026-06-30T10:00:00Z',
  },
  {
    id: 'py2',
    reference: 'PAY-FF-0038',
    order_reference: 'FF-2026-0038',
    gross_amount: '11.80',
    platform_fee: '1.18',
    net_amount: '10.62',
    status: 'PAID',
    created_at: '2026-06-27T08:20:00Z',
    paid_at: '2026-06-29T10:00:00Z',
  },
  {
    id: 'py3',
    reference: 'PAY-FF-0040',
    order_reference: 'FF-2026-0040',
    gross_amount: '12.40',
    platform_fee: '1.24',
    net_amount: '11.16',
    status: 'PROCESSING',
    created_at: '2026-06-29T14:35:00Z',
  },
  {
    id: 'py4',
    reference: 'PAY-FF-0041',
    order_reference: 'FF-2026-0041',
    gross_amount: '11.10',
    platform_fee: '1.11',
    net_amount: '9.99',
    status: 'PENDING',
    created_at: '2026-06-30T09:12:00Z',
  },
]

export type SupplierProductStatus = 'ACTIVE' | 'DRAFT' | 'ARCHIVED'

export interface SupplierProduct {
  id: string
  name: string
  sku: string
  category: string
  price: string
  unit: string
  stock_available: number
  low_stock_threshold: number
  status: SupplierProductStatus
  updated_at: string
}

export const SUPPLIER_PRODUCTS: SupplierProduct[] = [
  {
    id: 'p1',
    name: 'Carrots',
    sku: 'CARR-1KG',
    category: 'Produce',
    price: '2.50',
    unit: 'kg',
    stock_available: 48,
    low_stock_threshold: 10,
    status: 'ACTIVE',
    updated_at: '2026-06-28T10:00:00Z',
  },
  {
    id: 'p2',
    name: 'Spinach',
    sku: 'SPIN-200G',
    category: 'Produce',
    price: '1.80',
    unit: 'bag',
    stock_available: 31,
    low_stock_threshold: 10,
    status: 'ACTIVE',
    updated_at: '2026-06-27T14:00:00Z',
  },
  {
    id: 'p3',
    name: 'Tenderstem Broccoli',
    sku: 'BRCL-250G',
    category: 'Produce',
    price: '2.40',
    unit: 'bunch',
    stock_available: 6,
    low_stock_threshold: 8,
    status: 'ACTIVE',
    updated_at: '2026-06-30T08:00:00Z',
  },
  {
    id: 'p4',
    name: 'Heritage Tomatoes',
    sku: 'HMTM-500G',
    category: 'Produce',
    price: '3.80',
    unit: '500g',
    stock_available: 0,
    low_stock_threshold: 5,
    status: 'DRAFT',
    updated_at: '2026-06-25T09:00:00Z',
  },
]

export function trend(current: number, previous: number): number {
  if (previous === 0) return 0
  return Math.round(((current - previous) / previous) * 1000) / 10
}
