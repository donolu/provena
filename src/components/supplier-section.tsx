import { Star } from 'lucide-react'
import { ProductCard } from '@/components/product-card'
import type { Product, Supplier } from '@/types'

interface SupplierSectionProps {
  supplier: Supplier
  products: Product[]
  wishlist: Set<string>
  onAddToCart: (variantId: string) => void
  onToggleWishlist: (variantId: string) => void
}

export function SupplierSection({
  supplier,
  products,
  wishlist,
  onAddToCart,
  onToggleWishlist,
}: SupplierSectionProps) {
  return (
    <section aria-label={supplier.business_name}>
      {/* Specimen-label strip: name ─── location  ★ rating */}
      <div className="flex items-center gap-4 mb-6">
        <span className="text-[11px] uppercase tracking-[0.14em] font-sans font-semibold text-forest whitespace-nowrap">
          {supplier.business_name}
        </span>
        <div aria-hidden="true" className="flex-1 h-px bg-hoarfrost" />
        <span className="text-xs font-sans text-soil whitespace-nowrap">
          {supplier.location}
        </span>
        <div className="flex items-center gap-1 flex-shrink-0">
          <Star className="w-3 h-3 fill-marigold text-marigold" strokeWidth={0} />
          <span className="font-mono text-xs text-forest">{supplier.rating.toFixed(1)}</span>
        </div>
      </div>

      {/* Three-column product grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {products.map((product) => {
          const variantId = product.variants[0]?.id
          return (
            <ProductCard
              key={product.id}
              product={product}
              inWishlist={variantId ? wishlist.has(variantId) : false}
              onAddToCart={onAddToCart}
              onToggleWishlist={onToggleWishlist}
            />
          )
        })}
      </div>
    </section>
  )
}
