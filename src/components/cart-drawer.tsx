'use client'

import { useEffect } from 'react'
import { X, Minus, Plus, ShoppingBasket, Trash2 } from 'lucide-react'
import type { CartItem } from '@/lib/api/types'

interface CartDrawerProps {
  open: boolean
  onClose: () => void
  items: CartItem[]
  total: string
  onUpdateQuantity: (itemId: string, quantity: number) => void
  onRemove: (itemId: string) => void
}

export function CartDrawer({ open, onClose, items, total, onUpdateQuantity, onRemove }: CartDrawerProps) {
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  const totalCount = items.reduce((s, i) => s + i.quantity, 0)

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-forest/25 backdrop-blur-[2px] transition-opacity duration-300 ${
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
      />

      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Shopping cart"
        className={`fixed inset-y-0 right-0 z-50 flex w-full flex-col bg-white shadow-2xl transition-transform duration-300 ease-in-out sm:w-[400px] ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-hoarfrost px-6 py-4">
          <div className="flex items-baseline gap-2">
            <h2 className="text-sm font-sans font-semibold text-forest">Cart</h2>
            {totalCount > 0 && (
              <span className="font-mono text-xs text-soil">({totalCount} item{totalCount !== 1 ? 's' : ''})</span>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close cart"
            className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-mist transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-meadow"
          >
            <X className="h-4 w-4 text-soil" strokeWidth={1.5} />
          </button>
        </div>

        {/* Body */}
        {items.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
            <ShoppingBasket className="h-10 w-10 text-hoarfrost" strokeWidth={1} />
            <div>
              <p className="font-display italic text-xl text-forest">Your cart is empty.</p>
              <p className="mt-1 text-sm text-soil">Browse the catalogue to find something good.</p>
            </div>
            <button
              onClick={onClose}
              className="mt-2 text-xs font-sans font-medium text-meadow underline underline-offset-2 hover:text-forest transition-colors duration-150"
            >
              Back to catalogue
            </button>
          </div>
        ) : (
          <ul className="flex-1 divide-y divide-hoarfrost overflow-y-auto px-6">
            {items.map((item) => (
              <li key={item.id} className="py-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-display text-[15px] leading-snug text-forest">
                      {item.product_name}
                    </p>
                    <p className="mt-0.5 text-[11px] uppercase tracking-[0.1em] text-soil font-sans">
                      {item.variant_name} · {item.variant_sku}
                    </p>
                  </div>
                  <button
                    onClick={() => onRemove(item.id)}
                    aria-label={`Remove ${item.product_name} from cart`}
                    className="mt-0.5 flex-shrink-0 text-hoarfrost hover:text-soil transition-colors duration-150"
                  >
                    <Trash2 className="h-3.5 w-3.5" strokeWidth={1.5} />
                  </button>
                </div>

                <div className="mt-3 flex items-center justify-between">
                  <div className="flex items-center gap-0 border border-hoarfrost rounded overflow-hidden">
                    <button
                      onClick={() => onUpdateQuantity(item.id, item.quantity - 1)}
                      aria-label="Decrease quantity"
                      className="flex h-7 w-7 items-center justify-center text-soil hover:bg-mist hover:text-forest transition-colors duration-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-meadow"
                    >
                      <Minus className="h-3 w-3" strokeWidth={2} />
                    </button>
                    <span className="flex h-7 min-w-[2rem] items-center justify-center border-x border-hoarfrost font-mono text-xs text-forest select-none">
                      {item.quantity}
                    </span>
                    <button
                      onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
                      aria-label="Increase quantity"
                      className="flex h-7 w-7 items-center justify-center text-soil hover:bg-mist hover:text-forest transition-colors duration-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-meadow"
                    >
                      <Plus className="h-3 w-3" strokeWidth={2} />
                    </button>
                  </div>

                  <div className="text-right">
                    <span className="font-mono text-sm font-medium text-forest">£{item.subtotal}</span>
                    <p className="text-[10px] text-soil font-sans mt-0.5">
                      £{item.price} each
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}

        {items.length > 0 && (
          <div className="border-t border-hoarfrost px-6 py-5">
            <div className="flex items-baseline justify-between mb-4">
              <span className="text-sm font-sans text-soil">Subtotal</span>
              <span className="font-mono text-base font-semibold text-forest">£{total}</span>
            </div>
            <p className="text-[11px] text-soil font-sans mb-4">
              Shipping and taxes calculated at checkout.
            </p>
            <button className="w-full rounded bg-forest py-3 text-sm font-sans font-medium text-mist hover:bg-meadow transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-meadow focus-visible:ring-offset-2">
              Proceed to checkout
            </button>
          </div>
        )}
      </aside>
    </>
  )
}
