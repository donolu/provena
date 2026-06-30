'use client'

import { ShoppingBasket, User, ChevronDown } from 'lucide-react'

interface NavProps {
  cartCount: number
}

export function Nav({ cartCount }: NavProps) {
  return (
    <header className="sticky top-0 z-50 bg-mist/95 backdrop-blur-sm border-b border-hoarfrost">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Wordmark */}
        <a href="/catalogue" className="font-display italic text-xl tracking-wide text-forest select-none">
          Provena
        </a>

        {/* Right-side controls */}
        <nav className="flex items-center gap-5">
          <button
            className="flex items-center gap-1.5 text-sm text-soil hover:text-forest transition-colors duration-150"
            aria-label="Account menu"
          >
            <User className="w-4 h-4" strokeWidth={1.5} />
            <span className="hidden sm:inline">Account</span>
            <ChevronDown className="w-3 h-3" strokeWidth={1.5} />
          </button>

          <button
            className="relative flex items-center gap-2 text-sm font-medium text-forest hover:text-meadow transition-colors duration-150"
            aria-label={`Cart, ${cartCount} item${cartCount !== 1 ? 's' : ''}`}
          >
            <span className="relative">
              <ShoppingBasket className="w-5 h-5" strokeWidth={1.5} />
              {cartCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-marigold text-forest text-[10px] font-mono font-semibold rounded-full flex items-center justify-center leading-none">
                  {cartCount > 9 ? '9+' : cartCount}
                </span>
              )}
            </span>
            <span className="hidden sm:inline">Cart</span>
          </button>
        </nav>
      </div>
    </header>
  )
}
