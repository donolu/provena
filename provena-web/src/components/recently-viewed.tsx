'use client'

import { useSyncExternalStore } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ProductCard } from '@/components/product-card'
import { addToCart, addToWishlist, getWishlist, removeFromWishlist } from '@/lib/api/cart'
import { useAuthStore } from '@/store/auth'
import { useRecentlyViewed } from '@/store/recently-viewed'

// Hydration-safe "is this the client?" flag: false during SSR and the first
// client render (matching the server), true afterwards — without a hydration
// mismatch and without setState in an effect.
const subscribe = () => () => {}
const useHydrated = () =>
  useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  )

/**
 * "Recently viewed" strip, backed by the client-side persisted store. Renders
 * nothing until mounted (the store is only available on the client) and when
 * there is nothing to show. `excludeSlug` drops the current product on the PDP.
 */
export function RecentlyViewed({ excludeSlug }: { excludeSlug?: string }) {
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const products = useRecentlyViewed((s) => s.products)
  const hydrated = useHydrated()

  const { data: wishlistData } = useQuery({
    queryKey: ['wishlist'],
    queryFn: () => getWishlist(),
    enabled: !!user,
  })
  const wishlist = wishlistData?.results ?? []

  const addToCartMutation = useMutation<void, Error, string>({
    mutationFn: async (variantId) => {
      await addToCart(variantId, 1)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  const wishlistMutation = useMutation<void, Error, string>({
    mutationFn: async (variantId) => {
      const existing = wishlist.find((w) => w.variant === variantId)
      if (existing) await removeFromWishlist(existing.id)
      else await addToWishlist(variantId)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['wishlist'] }),
  })

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
            inWishlist={
              p.variants[0] ? wishlist.some((w) => w.variant === p.variants[0].id) : false
            }
            onAddToCart={(variantId) => addToCartMutation.mutate(variantId)}
            onToggleWishlist={(variantId) => wishlistMutation.mutate(variantId)}
          />
        ))}
      </div>
    </section>
  )
}
