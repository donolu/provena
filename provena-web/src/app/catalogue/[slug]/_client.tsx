'use client'

import { use, useEffect, useState } from 'react'
import Image from 'next/image'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, Heart, ShoppingBasket, Star } from 'lucide-react'
import Link from 'next/link'
import { Nav } from '@/components/nav'
import { CartDrawer } from '@/components/cart-drawer'
import { getProduct, getProductReviews, getRelatedProducts, submitReview } from '@/lib/api/catalogue'
import { ProductCard } from '@/components/product-card'
import { RecentlyViewed } from '@/components/recently-viewed'
import { useRecentlyViewed } from '@/store/recently-viewed'
import { getCart, addToCart, updateCartItem, removeCartItem as deleteCartItem, getWishlist, addToWishlist, removeFromWishlist } from '@/lib/api/cart'
import { useAuthStore } from '@/store/auth'
import type { ProductVariant } from '@/lib/api/types'

function StarRating({ value, max = 5 }: { value: number; max?: number }) {
  return (
    <span className="flex items-center gap-0.5" aria-label={`${value} out of ${max} stars`}>
      {Array.from({ length: max }).map((_, i) => (
        <Star
          key={i}
          className={`w-3.5 h-3.5 ${i < Math.round(value) ? 'fill-marigold text-marigold' : 'text-hoarfrost'}`}
          strokeWidth={1.5}
        />
      ))}
    </span>
  )
}

function InteractiveStars({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [hovered, setHovered] = useState(0)
  const display = hovered || value
  return (
    <span className="flex items-center gap-1">
      {Array.from({ length: 5 }).map((_, i) => (
        <button
          key={i}
          type="button"
          onMouseEnter={() => setHovered(i + 1)}
          onMouseLeave={() => setHovered(0)}
          onClick={() => onChange(i + 1)}
          aria-label={`Rate ${i + 1} star${i + 1 !== 1 ? 's' : ''}`}
        >
          <Star
            className={`w-5 h-5 transition-colors ${i < display ? 'fill-marigold text-marigold' : 'text-hoarfrost'}`}
            strokeWidth={1.5}
          />
        </button>
      ))}
    </span>
  )
}

export default function ProductDetailPage({
  params,
  initialProduct,
}: {
  params: Promise<{ slug: string }>
  initialProduct?: import('@/lib/api/types').Product
}) {
  const { slug } = use(params)
  const { user } = useAuthStore()
  const qc = useQueryClient()

  const [cartOpen, setCartOpen] = useState(false)
  const [selectedVariant, setSelectedVariant] = useState<ProductVariant | null>(null)
  const [qty, setQty] = useState(1)

  const { data: product, isPending: productPending } = useQuery({
    queryKey: ['product', slug],
    queryFn: () => getProduct(slug),
    initialData: initialProduct,
  })

  const activeVariant = selectedVariant ?? product?.variants.find((v) => v.is_active) ?? product?.variants[0] ?? null

  const { data: cart } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
  })

  const { data: wishlistData } = useQuery({
    queryKey: ['wishlist'],
    queryFn: () => getWishlist(),
    enabled: !!user,
  })

  const { data: reviewsData } = useQuery({
    queryKey: ['reviews', activeVariant?.id ?? ''],
    queryFn: () => getProductReviews(activeVariant!.id),
    enabled: !!activeVariant,
  })

  const wishlist = wishlistData?.results ?? []
  const reviews = reviewsData?.results ?? []

  const [selectedImage, setSelectedImage] = useState(0)

  const cartItemForVariant = cart?.items.find((i) => i.variant === activeVariant?.id)
  const wishlistItemForVariant = wishlist.find((w) => w.variant === activeVariant?.id)

  const addToCartMutation = useMutation({
    mutationFn: () => addToCart(activeVariant!.id, qty),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cart'] })
      setCartOpen(true)
    },
  })

  const updateCartMutation = useMutation<void, Error, { id: string; quantity: number }>({
    mutationFn: async ({ id, quantity }) => {
      if (quantity > 0) await updateCartItem(id, quantity)
      else await deleteCartItem(id)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  const removeCartMutation = useMutation({
    mutationFn: (id: string) => deleteCartItem(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cart'] }),
  })

  const wishlistMutation = useMutation<void, Error, void>({
    mutationFn: async () => {
      if (wishlistItemForVariant) await removeFromWishlist(wishlistItemForVariant.id)
      else await addToWishlist(activeVariant!.id)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['wishlist'] }),
  })

  // "You might also like"
  const { data: related = [] } = useQuery({
    queryKey: ['related', slug],
    queryFn: () => getRelatedProducts(slug),
  })

  const relatedInWishlist = (variantId: string) => wishlist.some((w) => w.variant === variantId)

  const relatedAddToCartMutation = useMutation<void, Error, string>({
    mutationFn: async (variantId) => {
      await addToCart(variantId, 1)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cart'] })
      setCartOpen(true)
    },
  })

  const relatedWishlistMutation = useMutation<void, Error, string>({
    mutationFn: async (variantId) => {
      const existing = wishlist.find((w) => w.variant === variantId)
      if (existing) await removeFromWishlist(existing.id)
      else await addToWishlist(variantId)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['wishlist'] }),
  })

  // Track this product as recently viewed (client-side, persisted).
  const addRecentlyViewed = useRecentlyViewed((s) => s.addProduct)
  useEffect(() => {
    if (product) addRecentlyViewed(product)
  }, [product, addRecentlyViewed])

  // Review form
  const [reviewRating, setReviewRating] = useState(0)
  const [reviewTitle, setReviewTitle] = useState('')
  const [reviewBody, setReviewBody] = useState('')
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [reviewSuccess, setReviewSuccess] = useState(false)

  const reviewMutation = useMutation({
    mutationFn: () => submitReview(activeVariant!.id, { rating: reviewRating, title: reviewTitle, body: reviewBody }),
    onSuccess: () => {
      setReviewSuccess(true)
      setReviewRating(0)
      setReviewTitle('')
      setReviewBody('')
      setReviewError(null)
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setReviewError(err.response?.data?.detail ?? 'Could not submit review.')
    },
  })

  const avgRating = reviews.length
    ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
    : null

  const images = product?.images ?? []
  const primaryImage = images.length > 0 ? images[selectedImage] ?? images[0] : null

  if (productPending) {
    return (
      <>
        <Nav cartCount={cart?.item_count ?? 0} onCartClick={() => setCartOpen(true)} />
        <main className="max-w-5xl mx-auto px-6 py-10">
          <p className="text-sm font-sans text-soil">Loading…</p>
        </main>
      </>
    )
  }

  if (!product) {
    return (
      <>
        <Nav cartCount={cart?.item_count ?? 0} onCartClick={() => setCartOpen(true)} />
        <main className="max-w-5xl mx-auto px-6 py-10">
          <p className="text-sm font-sans text-soil">Product not found.</p>
        </main>
      </>
    )
  }

  return (
    <>
      <Nav cartCount={cart?.item_count ?? 0} onCartClick={() => setCartOpen(true)} />

      <main className="max-w-5xl mx-auto px-6 py-10">
        <Link
          href="/catalogue"
          className="inline-flex items-center gap-1.5 text-xs font-sans text-soil hover:text-forest transition-colors mb-8"
        >
          <ChevronLeft className="w-3.5 h-3.5" strokeWidth={1.5} />
          Back to catalogue
        </Link>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
          {/* Image gallery */}
          <div className="space-y-3">
            <div className="relative aspect-square bg-mist rounded-xl overflow-hidden border border-hoarfrost flex items-center justify-center">
              {primaryImage ? (
                <Image
                  src={primaryImage.url}
                  alt={primaryImage.alt_text || product.name}
                  fill
                  className="object-cover"
                  sizes="(max-width: 1024px) 100vw, 50vw"
                />
              ) : (
                <div className="w-full h-full bg-gradient-to-br from-[#1E3D28] to-[#3D6B4F] flex items-center justify-center">
                  <span className="font-display italic text-white/40 text-2xl">{product.name[0]}</span>
                </div>
              )}
            </div>
            {images.length > 1 && (
              <div className="flex gap-2 overflow-x-auto pb-1">
                {images.map((img, idx) => (
                  <button
                    key={img.id}
                    onClick={() => setSelectedImage(idx)}
                    className={`relative w-16 h-16 rounded-lg overflow-hidden border-2 flex-shrink-0 transition-colors ${
                      idx === selectedImage ? 'border-forest' : 'border-hoarfrost'
                    }`}
                  >
                    <Image src={img.url} alt={img.alt_text || ''} fill className="object-cover" sizes="64px" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Product info */}
          <div className="space-y-5">
            <div>
              {product.category_name && (
                <p className="text-[10px] uppercase tracking-[0.14em] font-sans text-meadow font-medium mb-1">
                  {product.category_name}
                </p>
              )}
              <h1 className="font-display italic text-3xl text-forest leading-tight">{product.name}</h1>
              <p className="text-sm font-sans text-soil mt-1">
                by{' '}
                <Link
                  href={`/catalogue?supplier=${product.supplier_slug}`}
                  className="text-forest hover:text-meadow transition-colors"
                >
                  {product.supplier_name}
                </Link>
              </p>
              {avgRating !== null && (
                <div className="flex items-center gap-2 mt-2">
                  <StarRating value={avgRating} />
                  <span className="text-xs font-sans text-soil">
                    {avgRating.toFixed(1)} ({reviews.length} review{reviews.length !== 1 ? 's' : ''})
                  </span>
                </div>
              )}
            </div>

            {product.description && (
              <p className="text-sm font-sans text-soil leading-relaxed">{product.description}</p>
            )}

            {/* Variant selector */}
            {product.variants.length > 1 && (
              <div>
                <p className="text-[10px] uppercase tracking-[0.12em] font-sans text-soil font-medium mb-2">
                  Select size
                </p>
                <div className="flex flex-wrap gap-2">
                  {product.variants.filter((v) => v.is_active).map((v) => (
                    <button
                      key={v.id}
                      onClick={() => { setSelectedVariant(v); setQty(1) }}
                      className={`px-3 py-1.5 text-xs font-sans rounded-md border transition-colors ${
                        activeVariant?.id === v.id
                          ? 'bg-forest text-white border-forest'
                          : 'bg-white text-soil border-hoarfrost hover:border-forest hover:text-forest'
                      }`}
                    >
                      {v.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Price + add to cart */}
            {activeVariant && (
              <div className="space-y-4 pt-1">
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-2xl font-semibold text-forest">
                    £{activeVariant.price}
                  </span>
                  {activeVariant.compare_at_price && (
                    <span className="font-mono text-sm text-soil/50 line-through">
                      £{activeVariant.compare_at_price}
                    </span>
                  )}
                  {activeVariant.on_sale && activeVariant.discount_percent && (
                    <span className="text-[10px] font-sans font-semibold text-white bg-marigold px-1.5 py-0.5 rounded">
                      -{activeVariant.discount_percent}%
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {cartItemForVariant ? (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateCartMutation.mutate({ id: cartItemForVariant.id, quantity: cartItemForVariant.quantity - 1 })}
                        disabled={updateCartMutation.isPending}
                        className="w-8 h-8 rounded-full border border-hoarfrost flex items-center justify-center text-soil hover:text-forest hover:border-forest transition-colors disabled:opacity-40"
                      >
                        -
                      </button>
                      <span className="w-6 text-center text-sm font-mono font-medium text-forest">
                        {cartItemForVariant.quantity}
                      </span>
                      <button
                        onClick={() => updateCartMutation.mutate({ id: cartItemForVariant.id, quantity: cartItemForVariant.quantity + 1 })}
                        disabled={updateCartMutation.isPending}
                        className="w-8 h-8 rounded-full border border-hoarfrost flex items-center justify-center text-soil hover:text-forest hover:border-forest transition-colors disabled:opacity-40"
                      >
                        +
                      </button>
                      <button
                        onClick={() => setCartOpen(true)}
                        className="ml-2 text-xs font-sans text-meadow hover:text-forest underline-offset-2 hover:underline transition-colors"
                      >
                        View cart
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3">
                      <div className="flex items-center border border-hoarfrost rounded-md overflow-hidden">
                        <button
                          onClick={() => setQty((q) => Math.max(1, q - 1))}
                          className="px-3 py-2 text-soil hover:text-forest hover:bg-mist transition-colors text-sm"
                        >
                          -
                        </button>
                        <span className="px-3 py-2 text-sm font-mono text-forest border-x border-hoarfrost min-w-[2.5rem] text-center">
                          {qty}
                        </span>
                        <button
                          onClick={() => setQty((q) => q + 1)}
                          className="px-3 py-2 text-soil hover:text-forest hover:bg-mist transition-colors text-sm"
                        >
                          +
                        </button>
                      </div>
                      <button
                        onClick={() => addToCartMutation.mutate()}
                        disabled={addToCartMutation.isPending}
                        className="flex items-center gap-2 px-5 py-2.5 bg-forest text-white text-sm font-sans rounded-md hover:bg-meadow disabled:opacity-40 transition-colors"
                      >
                        <ShoppingBasket className="w-4 h-4" strokeWidth={1.5} />
                        Add to cart
                      </button>
                    </div>
                  )}

                  {user && (
                    <button
                      onClick={() => wishlistMutation.mutate()}
                      disabled={wishlistMutation.isPending}
                      aria-label={wishlistItemForVariant ? 'Remove from wishlist' : 'Add to wishlist'}
                      className="ml-auto flex items-center justify-center w-9 h-9 rounded-full border border-hoarfrost hover:border-marigold transition-colors disabled:opacity-40"
                    >
                      <Heart
                        className={`w-4 h-4 transition-colors ${
                          wishlistItemForVariant ? 'fill-marigold text-marigold' : 'text-soil'
                        }`}
                        strokeWidth={1.5}
                      />
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Reviews section */}
        <div className="mt-14 border-t border-hoarfrost pt-10">
          <div className="flex items-baseline gap-4 mb-6">
            <h2 className="font-display italic text-xl text-forest">Reviews</h2>
            {avgRating !== null && (
              <div className="flex items-center gap-2">
                <StarRating value={avgRating} />
                <span className="text-xs font-sans text-soil">{avgRating.toFixed(1)} average</span>
              </div>
            )}
          </div>

          {reviews.length === 0 ? (
            <p className="text-sm font-sans text-soil mb-8">No reviews yet for this variant.</p>
          ) : (
            <div className="space-y-5 mb-10">
              {reviews.map((review) => (
                <div key={review.id} className="bg-white rounded-lg border border-hoarfrost px-5 py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <StarRating value={review.rating} />
                      <p className="text-sm font-sans font-medium text-forest mt-1.5">{review.title}</p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      {review.is_verified_purchase && (
                        <span className="text-[10px] font-sans text-meadow font-medium bg-meadow/10 px-2 py-0.5 rounded-full">
                          Verified purchase
                        </span>
                      )}
                      <p className="text-[10px] font-sans text-soil/50 mt-1">
                        {new Date(review.created_at).toLocaleDateString('en-GB', {
                          day: 'numeric', month: 'short', year: 'numeric',
                        })}
                      </p>
                    </div>
                  </div>
                  <p className="text-xs font-sans text-soil mt-2 leading-relaxed">{review.body}</p>
                </div>
              ))}
            </div>
          )}

          {/* Submit review */}
          {user && !reviewSuccess && (
            <div className="bg-white rounded-lg border border-hoarfrost px-5 py-5">
              <p className="text-sm font-sans font-medium text-forest mb-4">Write a review</p>

              <div className="space-y-4">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.12em] font-sans text-soil font-medium mb-2">
                    Your rating
                  </p>
                  <InteractiveStars value={reviewRating} onChange={setReviewRating} />
                </div>

                <div>
                  <p className="text-[10px] uppercase tracking-[0.12em] font-sans text-soil font-medium mb-2">
                    Title
                  </p>
                  <input
                    type="text"
                    value={reviewTitle}
                    onChange={(e) => setReviewTitle(e.target.value)}
                    placeholder="Summarise your experience"
                    maxLength={200}
                    className="w-full text-xs font-sans border border-hoarfrost rounded px-3 py-2 focus:outline-none focus:border-meadow"
                  />
                </div>

                <div>
                  <p className="text-[10px] uppercase tracking-[0.12em] font-sans text-soil font-medium mb-2">
                    Review
                  </p>
                  <textarea
                    value={reviewBody}
                    onChange={(e) => setReviewBody(e.target.value)}
                    rows={4}
                    placeholder="Tell others about the quality, freshness, or delivery experience…"
                    className="w-full text-xs font-sans border border-hoarfrost rounded px-3 py-2 focus:outline-none focus:border-meadow resize-none"
                  />
                </div>

                {reviewError && <p className="text-xs font-sans text-red-600">{reviewError}</p>}

                <button
                  onClick={() => reviewMutation.mutate()}
                  disabled={
                    reviewMutation.isPending ||
                    reviewRating === 0 ||
                    !reviewTitle.trim() ||
                    !reviewBody.trim()
                  }
                  className="px-5 py-2.5 bg-forest text-white text-xs font-sans rounded-md hover:bg-meadow disabled:opacity-40 transition-colors"
                >
                  {reviewMutation.isPending ? 'Submitting…' : 'Submit review'}
                </button>
              </div>
            </div>
          )}

          {reviewSuccess && (
            <div className="bg-meadow/10 border border-meadow/30 rounded-lg px-5 py-4">
              <p className="text-sm font-sans text-forest font-medium">Review submitted</p>
              <p className="text-xs font-sans text-soil mt-1">
                Thank you. Your review will appear once approved by our team.
              </p>
            </div>
          )}

          {!user && (
            <p className="text-xs font-sans text-soil">
              <Link href="/login" className="text-meadow hover:text-forest transition-colors">Sign in</Link>{' '}
              to leave a review.
            </p>
          )}
        </div>

        {related.length > 0 && (
          <section className="mt-16 border-t border-hoarfrost pt-10">
            <h2 className="font-display italic text-xl text-forest mb-6">You might also like</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {related.map((p) => (
                <ProductCard
                  key={p.id}
                  product={p}
                  inWishlist={p.variants[0] ? relatedInWishlist(p.variants[0].id) : false}
                  onAddToCart={(variantId) => relatedAddToCartMutation.mutate(variantId)}
                  onToggleWishlist={(variantId) => relatedWishlistMutation.mutate(variantId)}
                />
              ))}
            </div>
          </section>
        )}

        <RecentlyViewed excludeSlug={slug} />
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
