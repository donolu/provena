import type { Product, ProductVariant } from '@/types'

export interface CartLineItem {
  variantId: string
  quantity: number
  product: Product
  variant: ProductVariant
  lineTotal: string
}

export function buildCartItems(
  cart: Map<string, number>,
  allProducts: Product[],
): CartLineItem[] {
  const lookup = new Map<string, { product: Product; variant: ProductVariant }>()
  for (const product of allProducts) {
    for (const variant of product.variants) {
      lookup.set(variant.id, { product, variant })
    }
  }

  return Array.from(cart.entries())
    .map(([variantId, quantity]) => {
      const entry = lookup.get(variantId)
      if (!entry) return null
      const lineTotal = (parseFloat(entry.variant.price) * quantity).toFixed(2)
      return { variantId, quantity, product: entry.product, variant: entry.variant, lineTotal }
    })
    .filter((x): x is CartLineItem => x !== null)
}

export function cartSubtotal(items: CartLineItem[]): string {
  const total = items.reduce((sum, item) => sum + parseFloat(item.lineTotal), 0)
  return total.toFixed(2)
}
