'use client'

import { useState } from 'react'
import { Heart } from 'lucide-react'
import type { Product } from '@/lib/api/types'

interface ProductCardProps {
  product: Product
  inWishlist: boolean
  onAddToCart: (variantId: string) => void
  onToggleWishlist: (variantId: string) => void
}

const CATEGORY_BG: Record<string, string> = {
  produce:  'from-[#1E3D28] to-[#3D6B4F]',
  dairy:    'from-[#9E8E6A] to-[#C4B48A]',
  grains:   'from-[#6A4A20] to-[#9C7A3C]',
  pantry:   'from-[#3C2818] to-[#60402A]',
  seasonal: 'from-[#3A1C48] to-[#6A3878]',
}

const CATEGORY_TEXT: Record<string, string> = {
  produce:  'text-white/50',
  dairy:    'text-[#3D2E1A]/40',
  grains:   'text-white/50',
  pantry:   'text-white/50',
  seasonal: 'text-white/50',
}

export function ProductCard({ product, inWishlist, onAddToCart, onToggleWishlist }: ProductCardProps) {
  const [added, setAdded]         = useState(false)
  const [wishlisted, setWishlisted] = useState(inWishlist)

  const variant      = product.variants[0]
  const categorySlug = product.category_slug ?? 'produce'
  const bg           = CATEGORY_BG[categorySlug] ?? 'from-forest to-meadow'
  const initialColor = CATEGORY_TEXT[categorySlug] ?? 'text-white/50'

  function handleAdd() {
    if (added || !variant) return
    onAddToCart(variant.id)
    setAdded(true)
    setTimeout(() => setAdded(false), 1800)
  }

  function handleWishlist(e: React.MouseEvent) {
    e.stopPropagation()
    const next = !wishlisted
    setWishlisted(next)
    onToggleWishlist(variant.id)
  }

  if (!variant) return null

  return (
    <div className="relative group">
      {/* Marigold crop marks — the signature element */}
      <span aria-hidden="true" className="crop-corner crop-tl" />
      <span aria-hidden="true" className="crop-corner crop-tr" />
      <span aria-hidden="true" className="crop-corner crop-bl" />
      <span aria-hidden="true" className="crop-corner crop-br" />

      <article className="bg-white rounded-lg overflow-hidden transition-shadow duration-150 group-hover:shadow-md">

        <div className={`relative w-full aspect-[4/3] bg-gradient-to-br overflow-hidden ${bg}`}>
          <span
            aria-hidden="true"
            className={`absolute -bottom-5 -right-3 font-display italic text-[130px] leading-none select-none pointer-events-none ${initialColor}`}
          >
            {product.name[0]}
          </span>

          <span className="absolute top-3 left-3 text-[10px] font-sans uppercase tracking-[0.12em] text-white/55 select-none">
            {product.category_name ?? product.category_slug}
          </span>

          <button
            onClick={handleWishlist}
            aria-label={wishlisted ? 'Remove from wishlist' : 'Save to wishlist'}
            className="absolute top-2.5 right-2.5 w-7 h-7 flex items-center justify-center rounded-full bg-white/15 backdrop-blur-sm hover:bg-white/30 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
          >
            <Heart
              className={`w-3.5 h-3.5 transition-all duration-150 ${
                wishlisted ? 'fill-marigold text-marigold' : 'text-white'
              }`}
              strokeWidth={1.5}
            />
          </button>

          {variant.on_sale && variant.discount_percent && (
            <span className="absolute bottom-3 left-3 font-mono text-[10px] text-marigold uppercase tracking-wide">
              {parseFloat(variant.discount_percent).toFixed(0)}% off
            </span>
          )}
        </div>

        <div className="p-4">
          <p className="text-[10px] uppercase tracking-[0.13em] text-soil font-sans mb-1">
            {product.supplier_name}
          </p>

          <h3 className="font-display text-[15px] leading-snug text-forest mb-3">
            {product.name}
            <span className="font-sans not-italic text-[13px] text-soil font-normal ml-1.5">
              · {variant.name}
            </span>
          </h3>

          <div className="flex items-center justify-between">
            <div className="flex items-baseline gap-1.5">
              <span className="font-mono text-sm font-medium text-forest">
                £{variant.price}
              </span>
              {variant.compare_at_price && (
                <span className="font-mono text-xs text-hoarfrost line-through">
                  £{variant.compare_at_price}
                </span>
              )}
            </div>

            <button
              onClick={handleAdd}
              className={[
                'text-xs font-sans font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:underline',
                added
                  ? 'text-meadow cursor-default'
                  : 'text-forest hover:text-meadow underline-offset-2 hover:underline',
              ].join(' ')}
            >
              {added ? 'Added ✓' : 'Add to cart'}
            </button>
          </div>
        </div>
      </article>
    </div>
  )
}
