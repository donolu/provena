'use client'

import { ProductCard } from '@/components/product-card'
import { useRecentlyViewed } from '@/store/recently-viewed'
import { useHydrated } from '@/hooks/use-hydrated'
import type { Product } from '@/lib/api/types'

interface RecentlyViewedProps {
  /** Drops the current product on the PDP. */
  excludeSlug?: string
  /**
   * Cart/wishlist are delegated to the host page so the strip shares the same
   * cart model (the homepage uses a local anonymous cart; the PDP uses the API
   * cart). Passing these avoids a strip that silently diverges from the page.
   */
  onAddToCart: (variantId: string) => void
  onToggleWishlist: (variantId: string) => void
  isInWishlist: (product: Product) => boolean
}

/**
 * "Recently viewed" strip, backed by the client-side persisted store. Renders
 * nothing until mounted (the store is only available on the client) and when
 * there is nothing to show.
 */
export function RecentlyViewed({
  excludeSlug,
  onAddToCart,
  onToggleWishlist,
  isInWishlist,
}: RecentlyViewedProps) {
  const products = useRecentlyViewed((s) => s.products)
  const hydrated = useHydrated()

  if (!hydrated) return null

  const items = products.filter((p) => p.slug !== excludeSlug).slice(0, 8)
  if (items.length === 0) return null

  return (
    <section className="mt-16 border-t border-hoarfrost pt-10">
      <h2 className="font-display italic text-xl text-forest mb-6">Recently viewed</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {items.map((p) => (
          <ProductCard
            key={p.id}
            product={p}
            inWishlist={isInWishlist(p)}
            onAddToCart={onAddToCart}
            onToggleWishlist={onToggleWishlist}
          />
        ))}
      </div>
    </section>
  )
}
