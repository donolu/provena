import { ProductCard } from '@/components/product-card'
import type { Product } from '@/lib/api/types'

interface SupplierSectionProps {
  supplierName: string
  supplierSlug: string
  products: Product[]
  wishlist: Set<string>
  onAddToCart: (variantId: string) => void
  onToggleWishlist: (variantId: string) => void
}

export function SupplierSection({
  supplierName,
  supplierSlug,
  products,
  wishlist,
  onAddToCart,
  onToggleWishlist,
}: SupplierSectionProps) {
  return (
    <section aria-label={supplierName}>
      <div className="flex items-center gap-4 mb-6">
        <span className="text-[11px] uppercase tracking-[0.14em] font-sans font-semibold text-forest whitespace-nowrap">
          {supplierName}
        </span>
        <div aria-hidden="true" className="flex-1 h-px bg-hoarfrost" />
        <span className="text-[10px] font-mono text-hoarfrost">{supplierSlug}</span>
      </div>

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
