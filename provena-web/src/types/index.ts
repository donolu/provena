export interface Supplier {
  id: string
  business_name: string
  slug: string
  location: string
  rating: number
}

export interface ProductVariant {
  id: string
  name: string
  sku: string
  price: string
  compare_at_price?: string
  unit: string
  stock_available: number
}

export interface Product {
  id: string
  name: string
  category_slug: string
  supplier: Supplier
  variants: ProductVariant[]
  review_count: number
}

export interface Category {
  id: string
  name: string
  slug: string
}

export interface CartEntry {
  variantId: string
  quantity: number
}
