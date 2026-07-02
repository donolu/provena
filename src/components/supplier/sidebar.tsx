'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  Package,
  ShoppingBag,
  Wallet,
  Menu,
  X,
  LogOut,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'

const NAV = [
  { href: '/supplier/dashboard', label: 'Overview',  icon: LayoutDashboard },
  { href: '/supplier/products',  label: 'Products',  icon: Package },
  { href: '/supplier/orders',    label: 'Orders',    icon: ShoppingBag },
  { href: '/supplier/payouts',   label: 'Payouts',   icon: Wallet },
]

function SidebarNav({ onLinkClick }: { onLinkClick?: () => void }) {
  const pathname = usePathname()
  const router = useRouter()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  function handleLogout() {
    logout()
    router.push('/login')
  }

  return (
    <div className="flex flex-col h-full">
      {/* Brand */}
      <div className="px-5 pt-6 pb-5 border-b border-white/10">
        <Link href="/supplier/dashboard" onClick={onLinkClick}>
          <span className="font-display italic text-xl text-white tracking-wide">Provena</span>
        </Link>
        <p className="text-[10px] uppercase tracking-[0.16em] text-meadow/70 font-sans mt-0.5">
          Supplier Portal
        </p>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              onClick={onLinkClick}
              className={[
                'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-sans transition-colors duration-150',
                active
                  ? 'bg-white/10 text-white font-medium'
                  : 'text-white/55 hover:text-white hover:bg-white/5',
              ].join(' ')}
            >
              {active && (
                <span className="absolute left-0 w-0.5 h-6 bg-meadow rounded-r" aria-hidden="true" />
              )}
              <Icon className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Supplier info */}
      <div className="px-4 py-4 border-t border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-meadow/30 flex items-center justify-center flex-shrink-0">
            <span className="text-[11px] font-mono font-semibold text-meadow">
              {user?.first_name?.[0] ?? 'S'}
            </span>
          </div>
          <div className="min-w-0">
            <p className="text-xs font-sans font-medium text-white truncate">
              {user?.first_name ?? 'Supplier'}
            </p>
            <p className="text-[10px] text-white/40 font-sans truncate">
              {user?.email ?? ''}
            </p>
          </div>
          <button
            onClick={handleLogout}
            aria-label="Sign out"
            className="ml-auto text-white/30 hover:text-white/70 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" strokeWidth={1.5} />
          </button>
        </div>
      </div>
    </div>
  )
}

export function SupplierShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex flex-col fixed inset-y-0 left-0 w-56 bg-forest z-30">
        <SidebarNav />
      </aside>

      {/* Mobile sidebar */}
      {mobileOpen && (
        <>
          <div
            aria-hidden="true"
            className="fixed inset-0 z-40 bg-forest/50 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="fixed inset-y-0 left-0 z-50 w-56 bg-forest lg:hidden">
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
              className="absolute top-4 right-4 text-white/50 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
            <SidebarNav onLinkClick={() => setMobileOpen(false)} />
          </aside>
        </>
      )}

      {/* Page area */}
      <div className="flex flex-col flex-1 lg:pl-56 min-w-0">
        {/* Mobile top bar */}
        <div className="lg:hidden flex items-center h-14 px-4 bg-white border-b border-hoarfrost flex-shrink-0">
          <button
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
            className="text-forest"
          >
            <Menu className="w-5 h-5" strokeWidth={1.5} />
          </button>
          <span className="ml-3 font-display italic text-forest text-lg">Provena</span>
        </div>

        <main className="flex-1 bg-mist overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
