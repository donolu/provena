'use client'

import { useRef, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ShoppingBasket, User, ChevronDown, LogOut, LogIn } from 'lucide-react'
import Link from 'next/link'
import { useAuthStore } from '@/store/auth'

interface NavProps {
  cartCount: number
  onCartClick: () => void
}

export function Nav({ cartCount, onCartClick }: NavProps) {
  const router = useRouter()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function handleLogout() {
    setOpen(false)
    logout()
    router.push('/login')
  }

  return (
    <header className="sticky top-0 z-50 bg-mist/95 backdrop-blur-sm border-b border-hoarfrost">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <a href="/catalogue" className="font-display italic text-xl tracking-wide text-forest select-none">
          Provena
        </a>

        <nav className="flex items-center gap-5">
          <div ref={ref} className="relative">
            <button
              onClick={() => setOpen((o) => !o)}
              className="flex items-center gap-1.5 text-sm text-soil hover:text-forest transition-colors duration-150"
              aria-label="Account menu"
              aria-expanded={open}
            >
              <User className="w-4 h-4" strokeWidth={1.5} />
              <span className="hidden sm:inline">
                {user ? user.first_name || 'Account' : 'Account'}
              </span>
              <ChevronDown className={`w-3 h-3 transition-transform duration-150 ${open ? 'rotate-180' : ''}`} strokeWidth={1.5} />
            </button>

            {open && (
              <div className="absolute right-0 top-full mt-2 w-48 bg-white border border-hoarfrost rounded-lg shadow-lg z-20 py-1 overflow-hidden">
                {user ? (
                  <>
                    <div className="px-4 py-2.5 border-b border-hoarfrost">
                      <p className="text-xs font-sans font-medium text-forest truncate">{user.first_name} {user.last_name}</p>
                      <p className="text-[10px] font-sans text-soil truncate">{user.email}</p>
                    </div>
                    <Link
                      href="/orders"
                      onClick={() => setOpen(false)}
                      className="flex items-center gap-2 w-full px-4 py-2.5 text-xs font-sans text-soil hover:text-forest hover:bg-mist transition-colors duration-100"
                    >
                      My orders
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 w-full px-4 py-2.5 text-xs font-sans text-soil hover:text-forest hover:bg-mist transition-colors duration-100"
                    >
                      <LogOut className="w-3.5 h-3.5" strokeWidth={1.5} />
                      Sign out
                    </button>
                  </>
                ) : (
                  <Link
                    href="/login"
                    onClick={() => setOpen(false)}
                    className="flex items-center gap-2 w-full px-4 py-2.5 text-xs font-sans text-soil hover:text-forest hover:bg-mist transition-colors duration-100"
                  >
                    <LogIn className="w-3.5 h-3.5" strokeWidth={1.5} />
                    Sign in
                  </Link>
                )}
              </div>
            )}
          </div>

          <button
            onClick={onCartClick}
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
