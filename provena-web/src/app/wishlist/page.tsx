'use client'

import { useQuery, useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { Heart, ShoppingBasket, Trash2 } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Nav } from '@/components/nav'
import { CartDrawer } from '@/components/cart-drawer'
import { getCart, addToCart, updateCartItem, removeCartItem, getWishlist, removeFromWishlist } from '@/lib/api/cart'
import { useAuthStore } from '@/store/auth'
import { useState } from 'react'

export default function WishlistPage() {
  const { user } = useAuthStore()
  const router = useRouter()
  const qc = useQueryClient()
  const [cartOpen, setCartOpen] = useState(false)
  const [loadedPages, setLoadedPages] = useState([1])

  const pageResults = useQueries({
    queries: loadedPages.map((p) => ({
      queryKey: ['wishlist', p],
      queryFn: () => getWishlist(p),
      enabled: !!user,
    })),
  })

  const lastResult = pageResults[pageResults.length - 1]
  const isPending = pageResults.some((r) => r.isPending)
  const allItems = pageResults.flatMap((r) => r.data?.results ?? [])
  const totalCount = pageResults[0]?.data?.count ?? allItems.length
  const hasMore = !!lastResult?.data?.next

  const { data: cart } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
    enabled: !!user,
  })

  const removeMutation = useMutation({
    mutationFn: (id: string) => removeFromWishlist(id),
    onSuccess: () => {
      setLoadedPages([1])
      qc.invalidateQueries({ queryKey: ['wishlist'] })
    },
  })

  const addToCartMutation = useMutation<void, Error, string>({
    mutationFn: async (variantId) => { await addToCart(variantId, 1) },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cart'] })
      setCartOpen(true)
    },
  })

  const updateCartMutation = useMutation<void, Error, { id: string; quantity: number }>({
    mutationFn: async ({ id, quantity }) => {
      if (quantity > 0) await updateCartItem(id, quantity)
      else await removeCartItem(id)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  const removeCartMutation = useMutation({
    mutationFn: (id: string) => removeCartItem(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  if (!user) {
    router.push('/login')
    return null
  }

  return (
    <>
      <Nav cartCount={cart?.item_count ?? 0} onCartClick={() => setCartOpen(true)} />

      <main className="max-w-3xl mx-auto px-6 py-10">
        <div className="flex items-center gap-3 mb-8">
          <Heart className="w-5 h-5 text-marigold" strokeWidth={1.5} />
          <div>
            <h1 className="font-display italic text-2xl text-forest">Saved items</h1>
            {!isPending && (
              <p className="text-xs font-sans text-soil mt-0.5">
                {totalCount} item{totalCount !== 1 ? 's' : ''}
              </p>
            )}
          </div>
        </div>

        {isPending && loadedPages.length === 1 ? (
          <p className="text-sm font-sans text-soil">Loading…</p>
        ) : allItems.length === 0 ? (
          <div className="text-center py-16">
            <Heart className="w-10 h-10 text-hoarfrost mx-auto mb-4" strokeWidth={1.5} />
            <p className="text-sm font-sans text-soil mb-4">Your wishlist is empty.</p>
            <Link
              href="/catalogue"
              className="inline-flex items-center gap-2 text-xs font-sans text-white bg-forest rounded-md px-4 py-2 hover:bg-meadow transition-colors"
            >
              Browse products
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {allItems.map((item) => {
              const cartItem = cart?.items.find((c) => c.variant === item.variant)
              return (
                <div
                  key={item.id}
                  className="bg-white rounded-lg border border-hoarfrost overflow-hidden"
                >
                  <div className="px-5 py-4 flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <Link
                        href={`/catalogue/${item.variant_sku.split('-')[0] ?? ''}`}
                        className="text-sm font-sans font-medium text-forest hover:text-meadow transition-colors"
                      >
                        {item.product_name}
                      </Link>
                      <p className="text-xs font-sans text-soil mt-0.5">
                        {item.variant_name} · SKU {item.variant_sku}
                      </p>
                      <p className="font-mono text-sm font-medium text-forest mt-1.5">
                        £{item.price}
                      </p>
                      {!item.is_active && (
                        <p className="text-[11px] font-sans text-red-500 mt-1">No longer available</p>
                      )}
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0 pt-0.5">
                      {item.is_active && (
                        cartItem ? (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => updateCartMutation.mutate({ id: cartItem.id, quantity: cartItem.quantity - 1 })}
                              disabled={updateCartMutation.isPending}
                              className="w-7 h-7 rounded-full border border-hoarfrost flex items-center justify-center text-soil hover:text-forest hover:border-forest transition-colors disabled:opacity-40 text-sm"
                            >
                              -
                            </button>
                            <span className="w-5 text-center text-xs font-mono font-medium text-forest">
                              {cartItem.quantity}
                            </span>
                            <button
                              onClick={() => updateCartMutation.mutate({ id: cartItem.id, quantity: cartItem.quantity + 1 })}
                              disabled={updateCartMutation.isPending}
                              className="w-7 h-7 rounded-full border border-hoarfrost flex items-center justify-center text-soil hover:text-forest hover:border-forest transition-colors disabled:opacity-40 text-sm"
                            >
                              +
                            </button>
                            <button
                              onClick={() => setCartOpen(true)}
                              aria-label="View cart"
                              className="ml-1 text-soil hover:text-forest transition-colors"
                            >
                              <ShoppingBasket className="w-4 h-4" strokeWidth={1.5} />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => addToCartMutation.mutate(item.variant)}
                            disabled={addToCartMutation.isPending}
                            className="flex items-center gap-1.5 text-xs font-sans text-white bg-forest rounded-md px-3 py-1.5 hover:bg-meadow disabled:opacity-40 transition-colors"
                          >
                            <ShoppingBasket className="w-3.5 h-3.5" strokeWidth={1.5} />
                            Add to cart
                          </button>
                        )
                      )}
                      <button
                        onClick={() => removeMutation.mutate(item.id)}
                        disabled={removeMutation.isPending}
                        aria-label="Remove from wishlist"
                        className="text-soil/40 hover:text-red-500 transition-colors disabled:opacity-40"
                      >
                        <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}

            {hasMore && (
              <div className="pt-2 text-center">
                <button
                  onClick={() => setLoadedPages((ps) => [...ps, ps.length + 1])}
                  disabled={isPending}
                  className="text-xs font-sans text-meadow hover:text-forest transition-colors disabled:opacity-40"
                >
                  {isPending ? 'Loading…' : 'Load more'}
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      <CartDrawer
        open={cartOpen}
        onClose={() => setCartOpen(false)}
        items={cart?.items ?? []}
        total={cart?.total ?? '0.00'}
        onUpdateQuantity={(id, quantity) => updateCartMutation.mutate({ id, quantity })}
        onRemove={(id) => removeCartMutation.mutate(id)}
      />
    </>
  )
}
