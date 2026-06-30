'use client'

import { useState } from 'react'
import { Plus, MoreHorizontal, AlertTriangle } from 'lucide-react'
import { StatusBadge } from '@/components/supplier/status-badge'
import { SUPPLIER_PRODUCTS, type SupplierProduct } from '@/lib/supplier-data'

function StockCell({ product }: { product: SupplierProduct }) {
  const isLow = product.stock_available > 0 && product.stock_available <= product.low_stock_threshold
  const isOut = product.stock_available === 0

  if (isOut) {
    return <span className="font-mono text-xs text-soil">Out of stock</span>
  }
  return (
    <div className="flex items-center gap-1.5">
      {isLow && <AlertTriangle className="w-3 h-3 text-marigold flex-shrink-0" strokeWidth={1.5} />}
      <span className={`font-mono text-xs ${isLow ? 'text-marigold' : 'text-forest'}`}>
        {product.stock_available}
      </span>
    </div>
  )
}

export default function ProductsPage() {
  const [products, setProducts] = useState(SUPPLIER_PRODUCTS)
  const [openMenu, setOpenMenu] = useState<string | null>(null)

  function toggleStatus(id: string) {
    setProducts((prev) =>
      prev.map((p) =>
        p.id === id
          ? { ...p, status: p.status === 'ACTIVE' ? 'DRAFT' : 'ACTIVE' as SupplierProduct['status'] }
          : p,
      ),
    )
    setOpenMenu(null)
  }

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display italic text-2xl text-forest">Products</h1>
          <p className="text-sm text-soil font-sans mt-0.5">{products.length} listing{products.length !== 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => alert('Product creation coming soon.')}
          className="flex items-center gap-2 bg-forest text-mist text-xs font-sans font-medium px-4 py-2.5 rounded hover:bg-meadow transition-colors duration-150"
        >
          <Plus className="w-3.5 h-3.5" strokeWidth={2} />
          New product
        </button>
      </div>

      <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-hoarfrost">
                <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Product</th>
                <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden sm:table-cell">SKU</th>
                <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden md:table-cell">Category</th>
                <th className="text-right px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Price</th>
                <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Stock</th>
                <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Status</th>
                <th className="px-4 py-3" aria-label="Actions" />
              </tr>
            </thead>
            <tbody className="divide-y divide-hoarfrost">
              {products.map((product) => (
                <tr key={product.id} className="hover:bg-mist/50 transition-colors duration-100">
                  <td className="px-4 py-3.5">
                    <p className="text-sm font-sans font-medium text-forest">{product.name}</p>
                  </td>
                  <td className="px-4 py-3.5 hidden sm:table-cell">
                    <span className="font-mono text-xs text-soil">{product.sku}</span>
                  </td>
                  <td className="px-4 py-3.5 hidden md:table-cell">
                    <span className="text-xs font-sans text-soil">{product.category}</span>
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <span className="font-mono text-xs text-forest">£{product.price}</span>
                    <span className="text-xs text-soil font-sans">/{product.unit}</span>
                  </td>
                  <td className="px-4 py-3.5"><StockCell product={product} /></td>
                  <td className="px-4 py-3.5"><StatusBadge status={product.status} /></td>
                  <td className="px-4 py-3.5 text-right relative">
                    <button
                      onClick={() => setOpenMenu(openMenu === product.id ? null : product.id)}
                      aria-label="Product actions"
                      className="p-1 rounded hover:bg-mist text-soil hover:text-forest transition-colors duration-100"
                    >
                      <MoreHorizontal className="w-4 h-4" strokeWidth={1.5} />
                    </button>

                    {openMenu === product.id && (
                      <>
                        <div className="fixed inset-0 z-10" onClick={() => setOpenMenu(null)} />
                        <div className="absolute right-4 top-full mt-1 w-44 bg-white border border-hoarfrost rounded-lg shadow-lg z-20 py-1 overflow-hidden">
                          <button
                            onClick={() => { setOpenMenu(null); alert('Edit coming soon.') }}
                            className="w-full text-left px-4 py-2.5 text-xs font-sans text-forest hover:bg-mist transition-colors duration-100"
                          >
                            Edit product
                          </button>
                          <button
                            onClick={() => toggleStatus(product.id)}
                            className="w-full text-left px-4 py-2.5 text-xs font-sans text-forest hover:bg-mist transition-colors duration-100"
                          >
                            {product.status === 'ACTIVE' ? 'Set to draft' : 'Set to active'}
                          </button>
                          <button
                            onClick={() => { setOpenMenu(null); alert('Stock update coming soon.') }}
                            className="w-full text-left px-4 py-2.5 text-xs font-sans text-forest hover:bg-mist transition-colors duration-100"
                          >
                            Update stock
                          </button>
                          <div className="h-px bg-hoarfrost my-1" />
                          <button
                            onClick={() => { setOpenMenu(null); alert('Archive coming soon.') }}
                            className="w-full text-left px-4 py-2.5 text-xs font-sans text-soil hover:bg-mist transition-colors duration-100"
                          >
                            Archive
                          </button>
                        </div>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
