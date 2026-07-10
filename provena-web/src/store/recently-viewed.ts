import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Product } from '@/lib/api/types'

const MAX_ITEMS = 8

interface RecentlyViewedState {
  products: Product[]
  addProduct: (product: Product) => void
}

/**
 * Recently viewed products, tracked client-side and persisted to localStorage.
 * Most-recent-first, deduplicated by slug, capped at MAX_ITEMS.
 */
export const useRecentlyViewed = create<RecentlyViewedState>()(
  persist(
    (set) => ({
      products: [],
      addProduct: (product) =>
        set((state) => ({
          products: [
            product,
            ...state.products.filter((p) => p.slug !== product.slug),
          ].slice(0, MAX_ITEMS),
        })),
    }),
    { name: 'provena-recently-viewed' },
  ),
)
