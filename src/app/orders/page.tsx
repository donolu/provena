'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { Nav } from '@/components/nav'
import { StatusBadge } from '@/components/supplier/status-badge'
import { Pagination } from '@/components/pagination'
import { getOrders } from '@/lib/api/orders'
import { getCart } from '@/lib/api/cart'
import { useAuthStore } from '@/store/auth'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function OrdersPage() {
  const { user } = useAuthStore()
  const [page, setPage] = useState(1)

  const { data, isPending } = useQuery({
    queryKey: ['orders', page],
    queryFn: () => getOrders(page),
    enabled: !!user,
  })

  const { data: cart } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
    enabled: !!user,
  })

  const orders = data?.results ?? []
  const totalCount = data?.count ?? 0

  return (
    <>
      <Nav cartCount={cart?.item_count ?? 0} onCartClick={() => {}} />

      <main className="max-w-3xl mx-auto px-6 py-10">
        <Link
          href="/catalogue"
          className="inline-flex items-center gap-1.5 text-xs font-sans text-soil hover:text-forest transition-colors duration-150 mb-8"
        >
          <ChevronLeft className="w-3.5 h-3.5" strokeWidth={1.5} />
          Continue shopping
        </Link>

        <div className="flex items-baseline justify-between mb-6">
          <h1 className="font-display italic text-2xl text-forest">My orders</h1>
          {totalCount > 0 && (
            <p className="text-xs font-sans text-soil">{totalCount} order{totalCount !== 1 ? 's' : ''}</p>
          )}
        </div>

        <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
          {isPending ? (
            <div className="px-4 py-12 text-center text-sm font-sans text-soil">Loading orders…</div>
          ) : orders.length === 0 ? (
            <div className="px-4 py-12 text-center">
              <p className="text-sm font-sans text-soil mb-2">No orders yet.</p>
              <Link href="/catalogue" className="text-xs font-sans text-meadow underline-offset-2 hover:underline">
                Browse the catalogue
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-hoarfrost">
                    {['Reference', 'Date', 'Total', 'Status', ''].map((h) => (
                      <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-hoarfrost">
                  {orders.map((order) => (
                    <tr key={order.id} className="hover:bg-mist/50 transition-colors duration-100">
                      <td className="px-4 py-3.5 font-mono text-xs text-forest">{order.reference}</td>
                      <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(order.created_at)}</td>
                      <td className="px-4 py-3.5 font-mono text-xs text-forest">£{order.total_amount}</td>
                      <td className="px-4 py-3.5"><StatusBadge status={order.status} /></td>
                      <td className="px-4 py-3.5 text-right">
                        <Link
                          href={`/orders/${order.reference}`}
                          className="text-xs font-sans text-meadow underline-offset-2 hover:underline"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Pagination page={page} count={totalCount} onChange={setPage} />
        </div>
      </main>
    </>
  )
}
