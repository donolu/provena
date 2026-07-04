'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { BarChart2, Package, ShoppingBag, Wallet } from 'lucide-react'
import { StatCard } from '@/components/supplier/stat-card'
import { StatusBadge } from '@/components/supplier/status-badge'
import { getSupplierSubOrders } from '@/lib/api/orders'
import { getMyProducts } from '@/lib/api/catalogue'
import { getSupplierPayouts } from '@/lib/api/admin'
import { getMyPerformance } from '@/lib/api/suppliers'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function DashboardPage() {
  const { data: summary } = useQuery({
    queryKey: ['supplier', 'performance'],
    queryFn: getMyPerformance,
  })

  const { data: subOrdersData } = useQuery({
    queryKey: ['supplier', 'suborders'],
    queryFn: () => getSupplierSubOrders(),
  })

  const { data: productsData } = useQuery({
    queryKey: ['supplier', 'products'],
    queryFn: () => getMyProducts(),
  })

  const { data: payoutsData } = useQuery({
    queryKey: ['supplier', 'payouts'],
    queryFn: () => getSupplierPayouts(),
  })

  const recentOrders = subOrdersData?.results.slice(0, 5) ?? []
  const products = productsData?.results ?? []
  const pendingPayout = (payoutsData?.results ?? [])
    .filter((p) => p.status === 'PENDING')
    .reduce((s, p) => s + parseFloat(p.net_amount), 0)
    .toFixed(2)

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display italic text-2xl text-forest">Overview</h1>
        <p className="text-sm text-soil font-sans mt-0.5">Last 30 days</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <StatCard
          label="Revenue"
          prefix="£"
          value={summary ? parseFloat(summary.total_revenue).toFixed(2) : '—'}
          icon={BarChart2}
        />
        <StatCard
          label="Orders"
          value={summary ? String(summary.total_orders) : '—'}
          icon={ShoppingBag}
        />
        <StatCard
          label="Pending payout"
          prefix="£"
          value={pendingPayout}
          icon={Wallet}
        />
        <StatCard
          label="Products"
          value={products.length ? String(products.length) : '—'}
          icon={Package}
        />
      </div>

      {/* Recent orders */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-sans font-semibold text-forest">Recent orders</h2>
          <Link href="/supplier/orders" className="text-xs font-sans text-meadow underline-offset-2 hover:underline">
            View all
          </Link>
        </div>

        <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  {['Reference', 'Date', 'Buyer', 'Subtotal', 'Status'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {recentOrders.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-sm font-sans text-soil">
                      No orders yet.
                    </td>
                  </tr>
                ) : recentOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3.5 font-mono text-xs text-forest">{order.order_reference}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(order.created_at)}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-forest">{order.buyer_email}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-forest">£{order.subtotal}</td>
                    <td className="px-4 py-3.5"><StatusBadge status={order.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Products quick view */}
      {products.length > 0 && (
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-sans font-semibold text-forest">Your products</h2>
            <Link href="/supplier/products" className="text-xs font-sans text-meadow underline-offset-2 hover:underline">
              Manage all
            </Link>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {products.slice(0, 6).map((p) => (
              <div key={p.id} className="bg-white rounded-lg border border-hoarfrost px-4 py-3.5 flex items-center justify-between">
                <div>
                  <p className="text-sm font-sans font-medium text-forest">{p.name}</p>
                  <p className="font-mono text-[11px] text-soil mt-0.5">{p.slug}</p>
                </div>
                <div className="text-right">
                  <StatusBadge status={p.status} />
                  <p className="font-mono text-xs text-forest mt-1">
                    £{p.variants[0]?.price ?? '—'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
