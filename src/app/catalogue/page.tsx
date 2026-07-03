'use client'

import { useMemo, useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, Search, X, SlidersHorizontal } from 'lucide-react'
import { Nav } from '@/components/nav'
import { CategoryTabs } from '@/components/category-tabs'
import { SupplierSection } from '@/components/supplier-section'
import { CartDrawer } from '@/components/cart-drawer'
import { getCategories, getProducts } from '@/lib/api/catalogue'
import { getCart, addToCart, updateCartItem, removeCartItem } from '@/lib/api/cart'
import { useAuthStore } from '@/store/auth'
import type { CartItem, Category, Product } from '@/lib/api/types'

const ALL: Category = {
  id: 'all', name: 'All', slug: 'all', description: '', image_url: null,
  parent_slug: null, children: [], position: 0, is_active: true, product_count: 0,
}

type SortKey = 'best-match' | 'price-asc' | 'price-desc'

const SORT_LABELS: Record<SortKey, string> = {
  'best-match': 'Best match',
  'price-asc':  'Price: low to high',
  'price-desc': 'Price: high to low',
}

function applySort(items: Product[], sort: SortKey): Product[] {
  const copy = [...items]
  if (sort === 'price-asc')  return copy.sort((a, b) => parseFloat(a.variants[0]?.price ?? '0') - parseFloat(b.variants[0]?.price ?? '0'))
  if (sort === 'price-desc') return copy.sort((a, b) => parseFloat(b.variants[0]?.price ?? '0') - parseFloat(a.variants[0]?.price ?? '0'))
  return copy
}

function groupBySupplier(products: Product[]) {
  const map = new Map<string, { supplierName: string; supplierSlug: string; products: Product[] }>()
  for (const p of products) {
    const key = p.supplier_slug
    if (!map.has(key)) map.set(key, { supplierName: p.supplier_name, supplierSlug: key, products: [] })
    map.get(key)!.products.push(p)
  }
  return Array.from(map.values())
}

function buildLocalCartItems(cart: Map<string, number>, products: Product[]): CartItem[] {
  return Array.from(cart.entries()).flatMap(([variantId, quantity]) => {
    for (const product of products) {
      const variant = product.variants.find((v) => v.id === variantId)
      if (variant) {
        return [{
          id: variantId,
          variant: variantId,
          variant_sku: variant.sku,
          variant_name: variant.name,
          product_name: product.name,
          price: variant.price,
          quantity,
          subtotal: (parseFloat(variant.price) * quantity).toFixed(2),
          reservation_expires_at: null,
          added_at: '',
          updated_at: '',
        } satisfies CartItem]
      }
    }
    return [] as CartItem[]
  })
}

export default function CataloguePage() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()

  const [activeCategory, setActiveCategory] = useState('all')
  const [sort, setSort]           = useState<SortKey>('best-match')
  const [sortOpen, setSortOpen]   = useState(false)
  const [cartOpen, setCartOpen]   = useState(false)
  const [filterOpen, setFilterOpen] = useState(false)
  const [search, setSearch]       = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [minPrice, setMinPrice]   = useState('')
  const [maxPrice, setMaxPrice]   = useState('')
  const [wishlist, setWishlist]   = useState<Set<string>>(new Set())
  const [localCart, setLocalCart] = useState<Map<string, number>>(new Map())
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    searchDebounceRef.current = setTimeout(() => setDebouncedSearch(search), 300)
    return () => { if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current) }
  }, [search])

  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
  })

  const productParams = useMemo(() => ({
    ...(activeCategory !== 'all' && { category: activeCategory }),
    ...(debouncedSearch && { search: debouncedSearch }),
    ...(minPrice && { min_price: parseFloat(minPrice) }),
    ...(maxPrice && { max_price: parseFloat(maxPrice) }),
  }), [activeCategory, debouncedSearch, minPrice, maxPrice])

  const { data: productsData, isPending: loadingProducts } = useQuery({
    queryKey: ['products', productParams],
    queryFn: () => getProducts(Object.keys(productParams).length ? productParams : undefined),
  })

  const { data: serverCart } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
    enabled: !!user,
  })

  const addMutation = useMutation({
    mutationFn: ({ variantId, qty }: { variantId: string; qty: number }) =>
      addToCart(variantId, qty),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cart'] }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ itemId, qty }: { itemId: string; qty: number }) =>
      updateCartItem(itemId, qty),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cart'] }),
  })

  const removeMutation = useMutation({
    mutationFn: (itemId: string) => removeCartItem(itemId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cart'] }),
  })

  const categories = useMemo(
    () => [ALL, ...(categoriesData ?? [])],
    [categoriesData],
  )

  const allProducts = useMemo(() => productsData?.results ?? [], [productsData])

  const filtered = useMemo(() => applySort(
    allProducts.filter((p) => p.status === 'ACTIVE'),
    sort,
  ), [allProducts, sort])

  const grouped = useMemo(() => groupBySupplier(filtered), [filtered])

  const cartItems: CartItem[] = useMemo(
    () => user && serverCart ? serverCart.items : buildLocalCartItems(localCart, allProducts),
    [user, serverCart, localCart, allProducts],
  )

  const cartTotal = user && serverCart
    ? serverCart.total
    : cartItems.reduce((s, i) => s + parseFloat(i.subtotal), 0).toFixed(2)

  const cartCount = cartItems.reduce((s, i) => s + i.quantity, 0)

  function handleAddToCart(variantId: string) {
    if (user) {
      addMutation.mutate({ variantId, qty: 1 })
    } else {
      setLocalCart((prev) => {
        const next = new Map(prev)
        next.set(variantId, (next.get(variantId) ?? 0) + 1)
        return next
      })
    }
  }

  function handleUpdateQuantity(itemId: string, quantity: number) {
    if (user) {
      quantity <= 0 ? removeMutation.mutate(itemId) : updateMutation.mutate({ itemId, qty: quantity })
    } else {
      setLocalCart((prev) => {
        const next = new Map(prev)
        if (quantity <= 0) next.delete(itemId)
        else next.set(itemId, quantity)
        return next
      })
    }
  }

  function handleRemoveFromCart(itemId: string) {
    if (user) {
      removeMutation.mutate(itemId)
    } else {
      setLocalCart((prev) => { const next = new Map(prev); next.delete(itemId); return next })
    }
  }

  function handleToggleWishlist(variantId: string) {
    setWishlist((prev) => {
      const next = new Set(prev)
      if (next.has(variantId)) next.delete(variantId)
      else next.add(variantId)
      return next
    })
  }

  return (
    <>
      <Nav cartCount={cartCount} onCartClick={() => setCartOpen(true)} />
      <CategoryTabs categories={categories} active={activeCategory} onSelect={setActiveCategory} />

      <main className="max-w-6xl mx-auto px-6 py-10">

        {/* Search bar */}
        <div className="relative mb-6">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-soil pointer-events-none" strokeWidth={1.5} />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search products, categories…"
            className="w-full pl-10 pr-10 py-2.5 text-sm font-sans text-forest bg-white border border-hoarfrost rounded-lg focus:outline-none focus:border-meadow placeholder:text-soil transition-colors duration-150"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-soil hover:text-forest transition-colors"
              aria-label="Clear search"
            >
              <X className="w-4 h-4" strokeWidth={1.5} />
            </button>
          )}
        </div>

        {/* Filter panel */}
        {filterOpen && (
          <div className="mb-6 p-4 bg-white border border-hoarfrost rounded-lg">
            <p className="text-xs font-sans font-semibold text-soil uppercase tracking-widest mb-3">Price range</p>
            <div className="flex items-center gap-3">
              <div className="relative flex-1">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-soil">£</span>
                <input
                  type="number"
                  min="0"
                  placeholder="Min"
                  value={minPrice}
                  onChange={(e) => setMinPrice(e.target.value)}
                  className="w-full pl-6 pr-3 py-2 text-sm font-sans text-forest border border-hoarfrost rounded focus:outline-none focus:border-meadow"
                />
              </div>
              <span className="text-xs text-soil">to</span>
              <div className="relative flex-1">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-soil">£</span>
                <input
                  type="number"
                  min="0"
                  placeholder="Max"
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(e.target.value)}
                  className="w-full pl-6 pr-3 py-2 text-sm font-sans text-forest border border-hoarfrost rounded focus:outline-none focus:border-meadow"
                />
              </div>
              {(minPrice || maxPrice) && (
                <button
                  onClick={() => { setMinPrice(''); setMaxPrice('') }}
                  className="text-xs font-sans text-soil hover:text-forest transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between mb-10">
          <p className="text-sm text-soil font-sans">
            <span className="font-mono text-forest font-medium">{filtered.length}</span>
            {' '}product{filtered.length !== 1 ? 's' : ''}
            {debouncedSearch && (
              <span className="ml-1.5">for <span className="text-forest italic">&ldquo;{debouncedSearch}&rdquo;</span></span>
            )}
          </p>

          <div className="flex items-center gap-3">
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
                  <div className="fixed inset-0 z-10" aria-hidden="true" onClick={() => setSortOpen(false)} />
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
                          sort === key ? 'text-forest font-medium bg-mist' : 'text-soil hover:text-forest hover:bg-mist',
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

            <button
              onClick={() => setFilterOpen((o) => !o)}
              className={[
                'flex items-center gap-1.5 text-xs font-sans border px-3 py-1.5 rounded transition-colors duration-150',
                (filterOpen || minPrice || maxPrice)
                  ? 'text-forest border-meadow bg-mist'
                  : 'text-forest border-hoarfrost hover:border-forest',
              ].join(' ')}
            >
              <SlidersHorizontal className="w-3 h-3" strokeWidth={1.5} />
              Filter
              {(minPrice || maxPrice) && <span className="w-1.5 h-1.5 rounded-full bg-meadow ml-0.5" />}
            </button>
          </div>
        </div>

        {loadingProducts ? (
          <div className="flex flex-col items-center justify-center py-28 text-center">
            <p className="font-display italic text-3xl text-hoarfrost mb-2">Loading…</p>
            <p className="text-sm text-soil">Fetching products from the catalogue.</p>
          </div>
        ) : grouped.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-28 text-center">
            <p className="font-display italic text-3xl text-hoarfrost mb-2">No results found.</p>
            <p className="text-sm text-soil">
              {debouncedSearch
                ? <>No products match &ldquo;<span className="text-forest italic">{debouncedSearch}</span>&rdquo;. Try a different term.</>
                : 'Try a different category or clear your filters.'}
            </p>
          </div>
        ) : (
          <div className="space-y-16">
            {grouped.map(({ supplierName, supplierSlug, products: sp }) => (
              <SupplierSection
                key={supplierSlug}
                supplierName={supplierName}
                supplierSlug={supplierSlug}
                products={sp}
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
        total={cartTotal}
        onUpdateQuantity={handleUpdateQuantity}
        onRemove={handleRemoveFromCart}
      />
    </>
  )
}
