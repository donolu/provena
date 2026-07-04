/* eslint-disable @next/next/no-img-element */
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { Nav } from '@/components/nav'
import { ProductCard } from '@/components/product-card'
import { CartDrawer } from '@/components/cart-drawer'
import { getProducts, getActiveBanners } from '@/lib/api/catalogue'
import { getCart, addToCart, updateCartItem, removeCartItem } from '@/lib/api/cart'
import { useAuthStore } from '@/store/auth'
import type { CartItem } from '@/lib/api/types'

export default function Home() {
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const [cartOpen, setCartOpen] = useState(false)
  const [wishlist, setWishlist] = useState<Set<string>>(new Set())
  const [localCart, setLocalCart] = useState<Map<string, number>>(new Map())

  const { data: featuredData } = useQuery({
    queryKey: ['products', 'featured'],
    queryFn: () => getProducts({ featured: true, page_size: 8 }),
  })

  const { data: banners = [] } = useQuery({
    queryKey: ['banners', 'active'],
    queryFn: getActiveBanners,
  })

  const { data: serverCart } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
    enabled: !!user,
  })

  const addMutation = useMutation({
    mutationFn: ({ variantId, qty }: { variantId: string; qty: number }) =>
      addToCart(variantId, qty),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ itemId, qty }: { itemId: string; qty: number }) =>
      updateCartItem(itemId, qty),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  const removeMutation = useMutation({
    mutationFn: (itemId: string) => removeCartItem(itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  const featured = featuredData?.results ?? []
  const allProducts = featured

  const cartItems: CartItem[] = (() => {
    if (user && serverCart) return serverCart.items
    return Array.from(localCart.entries()).flatMap(([variantId, quantity]) => {
      for (const p of allProducts) {
        const v = p.variants.find((v) => v.id === variantId)
        if (v) return [{ id: variantId, variant: variantId, variant_sku: v.sku, variant_name: v.name, product_name: p.name, price: v.price, quantity, subtotal: (parseFloat(v.price) * quantity).toFixed(2), reservation_expires_at: null, added_at: '', updated_at: '' } as CartItem]
      }
      return []
    })
  })()

  const cartCount = cartItems.reduce((s, i) => s + i.quantity, 0)
  const cartTotal = user && serverCart
    ? serverCart.total
    : cartItems.reduce((s, i) => s + parseFloat(i.subtotal), 0).toFixed(2)

  function handleAddToCart(variantId: string) {
    if (user) {
      addMutation.mutate({ variantId, qty: 1 })
    } else {
      setLocalCart((prev) => { const n = new Map(prev); n.set(variantId, (n.get(variantId) ?? 0) + 1); return n })
    }
  }

  function handleUpdateQuantity(itemId: string, quantity: number) {
    if (user) {
      quantity <= 0 ? removeMutation.mutate(itemId) : updateMutation.mutate({ itemId, qty: quantity })
    } else {
      setLocalCart((prev) => { const n = new Map(prev); quantity <= 0 ? n.delete(itemId) : n.set(itemId, quantity); return n })
    }
  }

  function handleRemoveFromCart(itemId: string) {
    if (user) {
      removeMutation.mutate(itemId)
    } else {
      setLocalCart((prev) => { const n = new Map(prev); n.delete(itemId); return n })
    }
  }

  function handleToggleWishlist(variantId: string) {
    setWishlist((prev) => { const n = new Set(prev); n.has(variantId) ? n.delete(variantId) : n.add(variantId); return n })
  }

  return (
    <>
      <Nav cartCount={cartCount} onCartClick={() => setCartOpen(true)} />

      {/* Hero */}
      <section className="relative overflow-hidden bg-forest">
        {/* Background texture */}
        <div aria-hidden="true" className="absolute inset-0 pointer-events-none">
          <span className="absolute -top-16 -right-16 font-display italic text-[320px] leading-none text-white/[0.04] select-none">P</span>
        </div>

        <div className="relative max-w-6xl mx-auto px-6 py-20 md:py-28">
          <p className="text-[10px] uppercase tracking-[0.22em] text-marigold font-sans mb-4">
            Artisan food marketplace
          </p>
          <h1 className="font-display italic text-4xl md:text-6xl text-white leading-tight max-w-2xl mb-6">
            Remarkable food,<br />
            direct from the source.
          </h1>
          <p className="text-base font-sans text-white/60 max-w-md mb-10 leading-relaxed">
            Hand-picked produce and provisions from small British farms and makers.
            No middlemen, no compromise.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <Link
              href="/catalogue"
              className="inline-flex items-center gap-2 px-6 py-3 bg-marigold text-forest text-sm font-sans font-medium rounded-lg hover:bg-marigold/90 transition-colors"
            >
              Browse all products
              <ArrowRight size={15} strokeWidth={2} />
            </Link>
            {!user && (
              <Link
                href="/register"
                className="text-sm font-sans text-white/60 hover:text-white underline-offset-2 hover:underline transition-colors"
              >
                Create an account
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* Promotional banners */}
      {banners.length > 0 && (
        <section className="max-w-6xl mx-auto px-6 pt-10">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {banners.map((banner) => (
              <div
                key={banner.id}
                className="relative rounded-xl overflow-hidden aspect-[16/6] bg-stone-200"
              >
                <img
                  src={banner.image_url}
                  alt={banner.title}
                  className="absolute inset-0 w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-forest/70 to-transparent" />
                <div className="absolute bottom-0 left-0 p-4">
                  <p className="font-display italic text-white text-lg leading-tight">{banner.title}</p>
                  {banner.subtitle && (
                    <p className="text-xs font-sans text-white/75 mt-0.5">{banner.subtitle}</p>
                  )}
                </div>
                {banner.link && (
                  <Link href={banner.link} className="absolute inset-0" aria-label={banner.title} />
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Featured products */}
      {featured.length > 0 && (
        <section className="max-w-6xl mx-auto px-6 py-14">
          <div className="flex items-baseline justify-between mb-8">
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-marigold font-sans mb-1">Editor&apos;s picks</p>
              <h2 className="font-display italic text-2xl text-forest">Featured this week</h2>
            </div>
            <Link
              href="/catalogue"
              className="text-xs font-sans text-soil hover:text-forest underline-offset-2 hover:underline transition-colors flex items-center gap-1"
            >
              All products <ArrowRight size={11} strokeWidth={2} />
            </Link>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {featured.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                inWishlist={product.variants.some((v) => wishlist.has(v.id))}
                onAddToCart={handleAddToCart}
                onToggleWishlist={handleToggleWishlist}
              />
            ))}
          </div>
        </section>
      )}

      {/* Empty state when no featured products yet */}
      {featured.length === 0 && (
        <section className="max-w-6xl mx-auto px-6 py-24 text-center">
          <h2 className="font-display italic text-2xl text-forest mb-3">Coming soon</h2>
          <p className="text-sm font-sans text-soil mb-6">Our curators are selecting the finest products.</p>
          <Link
            href="/catalogue"
            className="inline-flex items-center gap-2 text-sm font-sans text-forest hover:text-meadow underline-offset-2 hover:underline transition-colors"
          >
            Browse all products <ArrowRight size={13} strokeWidth={2} />
          </Link>
        </section>
      )}

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
