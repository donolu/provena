'use client'

import { useRef, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  ShoppingBasket,
  User,
  ChevronDown,
  Heart,
  LogOut,
  LogIn,
  Bell,
  X,
  Package,
  Truck,
  CheckCircle2,
  CreditCard,
  AlertCircle,
} from 'lucide-react'
import Link from 'next/link'
import { useRouter as useNextRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth'
import { logout as apiLogout } from '@/lib/api/auth'
import {
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  deleteNotification,
} from '@/lib/api/notifications'
import type { Notification, NotificationType } from '@/lib/api/types'

interface NavProps {
  cartCount: number
  onCartClick: () => void
}

function notifIcon(type: NotificationType) {
  switch (type) {
    case 'ORDER_PLACED':      return <Package className="w-3.5 h-3.5 text-meadow flex-shrink-0" strokeWidth={1.5} />
    case 'ORDER_DISPATCHED':  return <Truck className="w-3.5 h-3.5 text-marigold flex-shrink-0" strokeWidth={1.5} />
    case 'ORDER_DELIVERED':   return <CheckCircle2 className="w-3.5 h-3.5 text-meadow flex-shrink-0" strokeWidth={1.5} />
    case 'PAYMENT_SUCCEEDED': return <CreditCard className="w-3.5 h-3.5 text-forest flex-shrink-0" strokeWidth={1.5} />
    case 'LOW_STOCK':         return <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" strokeWidth={1.5} />
    default:                  return <Bell className="w-3.5 h-3.5 text-soil flex-shrink-0" strokeWidth={1.5} />
  }
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function NotificationBell({ user }: { user: { email: string; first_name: string } }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const qc = useQueryClient()
  const notifRouter = useNextRouter()

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const { data: notifData } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => getNotifications(),
    enabled: !!user,
    refetchInterval: 60_000,
  })

  const { data: unreadData } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: () => getNotifications(true),
    enabled: !!user,
    refetchInterval: 60_000,
  })

  const notifications = notifData?.results ?? []
  const unreadCount = unreadData?.count ?? 0

  const markReadMutation = useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteNotification(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })

  function handleNotifClick(notif: Notification) {
    if (!notif.is_read) markReadMutation.mutate(notif.id)
    const link = notif.data?.link as string | undefined
    if (link) {
      setOpen(false)
      notifRouter.push(link)
    }
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
        className="relative flex items-center justify-center text-soil hover:text-forest transition-colors duration-150"
      >
        <Bell className="w-5 h-5" strokeWidth={1.5} />
        {unreadCount > 0 && (
          <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-marigold text-forest text-[10px] font-mono font-semibold rounded-full flex items-center justify-center leading-none">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white border border-hoarfrost rounded-lg shadow-lg z-20 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-hoarfrost">
            <p className="text-xs font-sans font-semibold text-forest">Notifications</p>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllMutation.mutate()}
                disabled={markAllMutation.isPending}
                className="text-[10px] font-sans text-meadow hover:text-forest transition-colors disabled:opacity-40"
              >
                Mark all as read
              </button>
            )}
          </div>

          <ul className="max-h-80 overflow-y-auto divide-y divide-hoarfrost">
            {notifications.length === 0 ? (
              <li className="px-4 py-6 text-center">
                <p className="text-xs font-sans text-soil">No notifications yet.</p>
              </li>
            ) : (
              notifications.slice(0, 15).map((notif) => (
                <li
                  key={notif.id}
                  className={`group flex items-start gap-3 px-4 py-3 hover:bg-mist transition-colors cursor-pointer ${
                    notif.is_read ? 'opacity-60' : ''
                  }`}
                  onClick={() => handleNotifClick(notif)}
                >
                  <span className="mt-0.5">{notifIcon(notif.notification_type)}</span>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-sans ${notif.is_read ? 'text-soil' : 'font-medium text-forest'}`}>
                      {notif.title}
                    </p>
                    <p className="text-[11px] font-sans text-soil mt-0.5 leading-relaxed line-clamp-2">
                      {notif.body}
                    </p>
                    <p className="text-[10px] font-sans text-soil/50 mt-1">{timeAgo(notif.created_at)}</p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(notif.id) }}
                    aria-label="Dismiss notification"
                    className="ml-1 mt-0.5 opacity-0 group-hover:opacity-100 text-soil/40 hover:text-soil transition-opacity"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </li>
              ))
            )}
          </ul>

          <div className="px-4 py-2.5 border-t border-hoarfrost">
            <Link
              href="/account/notifications"
              onClick={() => setOpen(false)}
              className="text-[10px] font-sans text-meadow hover:text-forest transition-colors"
            >
              Notification settings
            </Link>
          </div>
        </div>
      )}
    </div>
  )
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

  async function handleLogout() {
    setOpen(false)
    apiLogout().catch(() => {})
    await logout()
    router.push('/login')
  }

  return (
    <header className="sticky top-0 z-50 bg-mist/95 backdrop-blur-sm border-b border-hoarfrost">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/catalogue" className="font-display italic text-xl tracking-wide text-forest select-none">
          Provena
        </Link>

        <nav className="flex items-center gap-5">
          {user && <NotificationBell user={user} />}

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
                    <Link
                      href="/wishlist"
                      onClick={() => setOpen(false)}
                      className="flex items-center gap-2 w-full px-4 py-2.5 text-xs font-sans text-soil hover:text-forest hover:bg-mist transition-colors duration-100"
                    >
                      <Heart className="w-3.5 h-3.5" strokeWidth={1.5} />
                      Saved items
                    </Link>
                    <Link
                      href="/account/payments"
                      onClick={() => setOpen(false)}
                      className="flex items-center gap-2 w-full px-4 py-2.5 text-xs font-sans text-soil hover:text-forest hover:bg-mist transition-colors duration-100"
                    >
                      <CreditCard className="w-3.5 h-3.5" strokeWidth={1.5} />
                      Payment history
                    </Link>
                    <Link
                      href="/account/notifications"
                      onClick={() => setOpen(false)}
                      className="flex items-center gap-2 w-full px-4 py-2.5 text-xs font-sans text-soil hover:text-forest hover:bg-mist transition-colors duration-100"
                    >
                      <Bell className="w-3.5 h-3.5" strokeWidth={1.5} />
                      Notifications
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
