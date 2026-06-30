'use client'

import Link from 'next/link'
import { Users, ShoppingBag, BarChart2, Store, AlertCircle } from 'lucide-react'
import { StatCard } from '@/components/supplier/stat-card'
import { StatusBadge } from '@/components/supplier/status-badge'
import {
  PLATFORM_STATS,
  ADMIN_SUPPLIERS,
  PLATFORM_ORDERS,
  trend,
} from '@/lib/admin-data'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function AdminDashboardPage() {
  const revTrend    = trend(parseFloat(PLATFORM_STATS.revenue_30d.replace(/\s/g, '')), parseFloat(PLATFORM_STATS.revenue_prev_30d.replace(/\s/g, '')))
  const ordersTrend = trend(PLATFORM_STATS.orders_30d, PLATFORM_STATS.orders_prev_30d)
  const usersTrend  = trend(PLATFORM_STATS.active_users, PLATFORM_STATS.active_users_prev)

  const pendingSuppliers = ADMIN_SUPPLIERS.filter((s) => s.status === 'PENDING')
  const recentOrders     = PLATFORM_ORDERS.slice(0, 6)

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display italic text-2xl text-forest">Overview</h1>
        <p className="text-sm text-soil font-sans mt-0.5">Platform metrics · last 30 days</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Revenue"      prefix="£" value={PLATFORM_STATS.revenue_30d}          icon={BarChart2} trend={{ pct: revTrend,    label: 'vs prev 30d' }} />
        <StatCard label="Orders"                  value={String(PLATFORM_STATS.orders_30d)}    icon={ShoppingBag} trend={{ pct: ordersTrend, label: 'vs prev 30d' }} />
        <StatCard label="Active users"            value={String(PLATFORM_STATS.active_users)}  icon={Users} trend={{ pct: usersTrend, label: 'vs prev 30d' }} />
        <StatCard label="Pending suppliers"       value={String(PLATFORM_STATS.pending_suppliers)} icon={Store} alert={PLATFORM_STATS.pending_suppliers > 0} />
      </div>

      {/* Pending supplier applications */}
      {pendingSuppliers.length > 0 && (
        <div className="mb-8 bg-marigold/8 border border-marigold/30 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-marigold" strokeWidth={1.5} />
              <p className="text-sm font-sans font-semibold text-forest">
                {pendingSuppliers.length} supplier application{pendingSuppliers.length !== 1 ? 's' : ''} awaiting review
              </p>
            </div>
            <Link href="/admin/suppliers" className="text-xs font-sans text-meadow underline-offset-2 hover:underline">
              Review all
            </Link>
          </div>
          <div className="space-y-2">
            {pendingSuppliers.map((s) => (
              <div key={s.id} className="flex items-center justify-between bg-white/60 rounded px-3 py-2.5">
                <div>
                  <p className="text-sm font-sans font-medium text-forest">{s.business_name}</p>
                  <p className="text-[11px] font-sans text-soil">{s.location} · applied {formatDate(s.joined_at)}</p>
                </div>
                <Link href="/admin/suppliers" className="text-xs font-sans text-meadow underline-offset-2 hover:underline flex-shrink-0">
                  Review
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent orders */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-sans font-semibold text-forest">Recent orders</h2>
          <Link href="/admin/orders" className="text-xs font-sans text-meadow underline-offset-2 hover:underline">View all</Link>
        </div>
        <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  {['Reference', 'Date', 'Buyer', 'Suppliers', 'Total', 'Status'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {recentOrders.map((o) => (
                  <tr key={o.id} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3.5 font-mono text-xs text-forest">{o.reference}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(o.created_at)}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-forest">{o.buyer_name}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil">{o.supplier_names.join(', ')}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-forest">£{o.total}</td>
                    <td className="px-4 py-3.5"><StatusBadge status={o.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
