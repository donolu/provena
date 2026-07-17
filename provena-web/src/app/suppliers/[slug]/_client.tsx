'use client'

import { use, useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ExternalLink, MapPin, Star, Truck } from 'lucide-react'
import { Nav } from '@/components/nav'
import { CartDrawer } from '@/components/cart-drawer'
import { ProductCard } from '@/components/product-card'
import { getPublicSupplier } from '@/lib/api/suppliers'
import { getProducts } from '@/lib/api/catalogue'
import { getCart, addToCart, updateCartItem, removeCartItem } from '@/lib/api/cart'
import { useAuthStore } from '@/store/auth'
import type { CartItem, Product, PublicSupplier } from '@/lib/api/types'

function StarRating({ value, count }: { value: number; count: number }) {
  return (
    <span className="flex items-center gap-1.5" aria-label={`${value} out of 5 stars from ${count} review${count !== 1 ? 's' : ''}`}>
      <span className="flex items-center gap-0.5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Star
            key={i}
            className={`w-3.5 h-3.5 ${i < Math.round(value) ? 'fill-marigold text-marigold' : 'text-hoarfrost'}`}
            strokeWidth={1.5}
          />
        ))}
      </span>
      <span className="text-xs font-mono text-soil">{value.toFixed(1)}</span>
      <span className="text-xs text-soil">({count})</span>
    </span>
  )
}

function deliveryLabel(s: PublicSupplier): string {
  if (s.shipping_policy === 'PER_ITEM') {
    return `£${s.shipping_per_item_rate} delivery per item`
  }
  if (s.shipping_policy === 'FREE_OVER_THRESHOLD' && s.free_shipping_threshold) {
    return `Free delivery over £${s.free_shipping_threshold}`
  }
  return Number(s.shipping_flat_rate) === 0 ? 'Free delivery' : `£${s.shipping_flat_rate} delivery`
}

export default function SupplierStorefrontPage({
  params,
  initialSupplier,
  initialProducts,
}: {
  params: Promise<{ slug: string }>
  initialSupplier?: PublicSupplier
  initialProducts?: Product[]
}) {
  const { slug } = use(params)
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const [cartOpen, setCartOpen] = useState(false)
  const [wishlist, setWishlist] = useState<Set<string>>(new Set())

  const { data: supplier } = useQuery({
    queryKey: ['supplier', slug],
    queryFn: () => getPublicSupplier(slug),
    initialData: initialSupplier,
  })

  const { data: productsData, isPending: loadingProducts } = useQuery({
    queryKey: ['products', { supplier: slug }],
    queryFn: () => getProducts({ supplier: slug }),
    initialData: initialProducts ? { results: initialProducts, count: initialProducts.length, next: null, previous: null } : undefined,
  })

  const { data: cart } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
    enabled: !!user,
  })

  const addMutation = useMutation({
    mutationFn: ({ variantId, qty }: { variantId: string; qty: number }) => addToCart(variantId, qty),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ itemId, qty }: { itemId: string; qty: number }) => updateCartItem(itemId, qty),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  const removeMutation = useMutation({
    mutationFn: (itemId: string) => removeCartItem(itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  const products = productsData?.results ?? []

  const cartItems: CartItem[] = cart?.items ?? []
  const cartTotal = cart?.total ?? '0.00'
  const cartCount = cartItems.reduce((s, i) => s + i.quantity, 0)

  function handleAddToCart(variantId: string) {
    if (user) addMutation.mutate({ variantId, qty: 1 })
  }

  function handleUpdateQuantity(itemId: string, quantity: number) {
    if (!user) return
    quantity <= 0 ? removeMutation.mutate(itemId) : updateMutation.mutate({ itemId, qty: quantity })
  }

  function handleRemoveFromCart(itemId: string) {
    if (user) removeMutation.mutate(itemId)
  }

  function handleToggleWishlist(variantId: string) {
    setWishlist((prev) => {
      const next = new Set(prev)
      if (next.has(variantId)) next.delete(variantId)
      else next.add(variantId)
      return next
    })
  }

  if (!supplier) {
    return (
      <>
        <Nav cartCount={0} onCartClick={() => setCartOpen(true)} />
        <main className="max-w-6xl mx-auto px-6 py-20 text-center">
          <p className="font-display italic text-3xl text-hoarfrost mb-2">Supplier not found.</p>
          <p className="text-sm text-soil mb-6">This storefront may have moved or been removed.</p>
          <Link href="/catalogue" className="text-sm font-sans text-forest underline hover:text-meadow transition-colors">
            Back to catalogue
          </Link>
        </main>
      </>
    )
  }

  const city = supplier.address?.city
  const locationLabel = [city, supplier.address?.county].filter(Boolean).join(', ')

  return (
    <>
      <Nav cartCount={cartCount} onCartClick={() => setCartOpen(true)} />

      <main className="max-w-6xl mx-auto px-6 py-10">
        {/* Back link */}
        <Link
          href="/catalogue"
          className="inline-flex items-center gap-1.5 text-xs font-sans text-soil hover:text-forest transition-colors duration-150 mb-8"
        >
          <ChevronLeft className="w-3.5 h-3.5" strokeWidth={1.5} />
          Back to catalogue
        </Link>

        {/* Supplier header */}
        <div className="flex items-start gap-6 mb-10 pb-10 border-b border-hoarfrost">
          {supplier.logo_url ? (
            <div className="relative w-20 h-20 rounded-lg overflow-hidden border border-hoarfrost flex-shrink-0">
              <Image
                src={supplier.logo_url}
                alt={supplier.business_name}
                fill
                className="object-cover"
                sizes="80px"
              />
            </div>
          ) : (
            <div className="w-20 h-20 rounded-lg border border-hoarfrost bg-mist flex items-center justify-center flex-shrink-0">
              <span className="font-display italic text-2xl text-hoarfrost">
                {supplier.business_name.charAt(0)}
              </span>
            </div>
          )}

          <div className="flex-1 min-w-0">
            <h1 className="font-display italic text-3xl text-forest mb-1">
              {supplier.business_name}
            </h1>

            <div className="flex flex-wrap items-center gap-3 mb-3">
              {supplier.average_rating !== null && (
                <StarRating value={supplier.average_rating} count={supplier.product_count} />
              )}
              <span className="text-xs font-mono text-soil">
                {supplier.product_count} product{supplier.product_count !== 1 ? 's' : ''}
              </span>
              {locationLabel && (
                <span className="flex items-center gap-1 text-xs text-soil">
                  <MapPin className="w-3 h-3" strokeWidth={1.5} />
                  {locationLabel}
                </span>
              )}
              <span className="flex items-center gap-1 text-xs text-soil">
                <Truck className="w-3 h-3" strokeWidth={1.5} />
                {deliveryLabel(supplier)}
              </span>
              {supplier.website && (
                <a
                  href={supplier.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-forest hover:text-meadow transition-colors duration-150"
                >
                  <ExternalLink className="w-3 h-3" strokeWidth={1.5} />
                  Website
                </a>
              )}
            </div>

            {supplier.description && (
              <p className="text-sm font-sans text-soil leading-relaxed max-w-2xl">
                {supplier.description}
              </p>
            )}
          </div>
        </div>

        {/* Product grid */}
        <div className="flex items-center gap-4 mb-8">
          <p className="text-[11px] uppercase tracking-[0.14em] font-sans font-semibold text-forest whitespace-nowrap">
            Products
          </p>
          <div aria-hidden="true" className="flex-1 h-px bg-hoarfrost" />
          <span className="text-[10px] font-mono text-hoarfrost">{products.length} listed</span>
        </div>

        {loadingProducts ? (
          <div className="flex flex-col items-center justify-center py-28 text-center">
            <p className="font-display italic text-3xl text-hoarfrost mb-2">Loading…</p>
          </div>
        ) : products.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-28 text-center">
            <p className="font-display italic text-3xl text-hoarfrost mb-2">No products listed.</p>
            <p className="text-sm text-soil">This supplier has no active products at the moment.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {products.map((product) => {
              const variantId = product.variants[0]?.id
              return (
                <ProductCard
                  key={product.id}
                  product={product}
                  inWishlist={variantId ? wishlist.has(variantId) : false}
                  onAddToCart={handleAddToCart}
                  onToggleWishlist={handleToggleWishlist}
                />
              )
            })}
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
