'use client'

import { useMemo, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { Nav } from '@/components/nav'
import { CategoryTabs } from '@/components/category-tabs'
import { SupplierSection } from '@/components/supplier-section'
import { CartDrawer } from '@/components/cart-drawer'
import { categories, groupBySupplier, products } from '@/lib/mock-data'
import { buildCartItems } from '@/lib/cart-utils'

type SortKey = 'best-match' | 'price-asc' | 'price-desc' | 'rating'

const SORT_LABELS: Record<SortKey, string> = {
  'best-match': 'Best match',
  'price-asc':  'Price: low to high',
  'price-desc': 'Price: high to low',
  'rating':     'Highest rated',
}

function applySort(items: typeof products, sort: SortKey) {
  const copy = [...items]
  switch (sort) {
    case 'price-asc':
      return copy.sort((a, b) => parseFloat(a.variants[0].price) - parseFloat(b.variants[0].price))
    case 'price-desc':
      return copy.sort((a, b) => parseFloat(b.variants[0].price) - parseFloat(a.variants[0].price))
    case 'rating':
      return copy.sort((a, b) => b.supplier.rating - a.supplier.rating)
    default:
      return copy
  }
}

export default function CataloguePage() {
  const [activeCategory, setActiveCategory] = useState('all')
  const [sort, setSort]         = useState<SortKey>('best-match')
  const [sortOpen, setSortOpen] = useState(false)
  const [cart, setCart]         = useState<Map<string, number>>(new Map())
  const [cartOpen, setCartOpen] = useState(false)
  const [wishlist, setWishlist] = useState<Set<string>>(new Set())

  const filtered = useMemo(() => {
    const base = activeCategory === 'all'
      ? products
      : products.filter((p) => p.category_slug === activeCategory)
    return applySort(base, sort)
  }, [activeCategory, sort])

  const grouped = useMemo(() => groupBySupplier(filtered), [filtered])

  const cartItems = useMemo(() => buildCartItems(cart, products), [cart])

  const cartCount = useMemo(
    () => cartItems.reduce((s, item) => s + item.quantity, 0),
    [cartItems],
  )

  function handleAddToCart(variantId: string) {
    setCart((prev) => {
      const next = new Map(prev)
      next.set(variantId, (next.get(variantId) ?? 0) + 1)
      return next
    })
  }

  function handleUpdateQuantity(variantId: string, quantity: number) {
    setCart((prev) => {
      const next = new Map(prev)
      if (quantity <= 0) {
        next.delete(variantId)
      } else {
        next.set(variantId, quantity)
      }
      return next
    })
  }

  function handleRemoveFromCart(variantId: string) {
    setCart((prev) => {
      const next = new Map(prev)
      next.delete(variantId)
      return next
    })
  }

  function handleToggleWishlist(variantId: string) {
    setWishlist((prev) => {
      const next = new Set(prev)
      if (next.has(variantId)) {
        next.delete(variantId)
      } else {
        next.add(variantId)
      }
      return next
    })
  }

  return (
    <>
      <Nav cartCount={cartCount} onCartClick={() => setCartOpen(true)} />
      <CategoryTabs categories={categories} active={activeCategory} onSelect={setActiveCategory} />

      <main className="max-w-6xl mx-auto px-6 py-10">

        {/* Filter bar */}
        <div className="flex items-center justify-between mb-10">
          <p className="text-sm text-soil font-sans">
            <span className="font-mono text-forest font-medium">{filtered.length}</span>
            {' '}product{filtered.length !== 1 ? 's' : ''}
          </p>

          <div className="flex items-center gap-3">
            {/* Sort dropdown */}
            <div className="relative">
              <button
                onClick={() => setSortOpen((o) => !o)}
                className="flex items-center gap-1.5 text-xs font-sans text-soil hover:text-forest transition-colors duration-150"
                aria-expanded={sortOpen}
                aria-haspopup="listbox"
              >
                <span>Sort: {SORT_LABELS[sort]}</span>
                <ChevronDown
                  className={`w-3 h-3 transition-transform duration-150 ${sortOpen ? 'rotate-180' : ''}`}
                  strokeWidth={1.5}
                />
              </button>

              {sortOpen && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    aria-hidden="true"
                    onClick={() => setSortOpen(false)}
                  />
                  <div
                    role="listbox"
                    className="absolute right-0 top-full mt-2 w-48 bg-white border border-hoarfrost rounded-lg shadow-lg z-20 py-1 overflow-hidden"
                  >
                    {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => (
                      <button
                        key={key}
                        role="option"
                        aria-selected={sort === key}
                        onClick={() => { setSort(key); setSortOpen(false) }}
                        className={[
                          'w-full text-left px-4 py-2.5 text-xs font-sans transition-colors duration-100',
                          sort === key
                            ? 'text-forest font-medium bg-mist'
                            : 'text-soil hover:text-forest hover:bg-mist',
                        ].join(' ')}
                      >
                        {SORT_LABELS[key]}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            <div aria-hidden="true" className="h-3.5 w-px bg-hoarfrost" />

            <button className="text-xs font-sans text-forest border border-hoarfrost px-3 py-1.5 rounded hover:border-forest transition-colors duration-150">
              Filter
            </button>
          </div>
        </div>

        {/* Supplier sections */}
        {grouped.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-28 text-center">
            <p className="font-display italic text-3xl text-hoarfrost mb-2">
              Nothing here yet.
            </p>
            <p className="text-sm text-soil">Try a different category or clear the filter.</p>
          </div>
        ) : (
          <div className="space-y-16">
            {grouped.map(({ supplier, products: sectionProducts }) => (
              <SupplierSection
                key={supplier.id}
                supplier={supplier}
                products={sectionProducts}
                wishlist={wishlist}
                onAddToCart={handleAddToCart}
                onToggleWishlist={handleToggleWishlist}
              />
            ))}
          </div>
        )}
      </main>

      <CartDrawer
        open={cartOpen}
        onClose={() => setCartOpen(false)}
        items={cartItems}
        onUpdateQuantity={handleUpdateQuantity}
        onRemove={handleRemoveFromCart}
      />
    </>
  )
}
