'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { Users, ShoppingBag, BarChart2, Store, AlertCircle } from 'lucide-react'
import { StatCard } from '@/components/supplier/stat-card'
import { StatusBadge } from '@/components/supplier/status-badge'
import { getAdminSuppliers } from '@/lib/api/suppliers'
import { getAdminOrders } from '@/lib/api/orders'
import { getSalesSummary } from '@/lib/api/admin'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function AdminDashboardPage() {
  const { data: salesData } = useQuery({
    queryKey: ['admin', 'analytics', 'sales'],
    queryFn: () => getSalesSummary({ days: 30 }),
  })

  const { data: suppliersData } = useQuery({
    queryKey: ['admin', 'suppliers', 'all'],
    queryFn: () => getAdminSuppliers({ page_size: 100 } as Parameters<typeof getAdminSuppliers>[0]),
  })

  const { data: ordersData } = useQuery({
    queryKey: ['admin', 'orders'],
    queryFn: getAdminOrders,
  })

  const pendingSuppliers = (suppliersData?.results ?? []).filter((s) => s.status === 'PENDING')
  const recentOrders = (ordersData?.results ?? []).slice(0, 6)
  const totalSuppliers = suppliersData?.count ?? 0

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display italic text-2xl text-forest">Overview</h1>
        <p className="text-sm text-soil font-sans mt-0.5">Platform metrics · last 30 days</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Revenue"
          prefix="£"
          value={salesData ? parseFloat(salesData.total_revenue).toFixed(2) : '—'}
          icon={BarChart2}
        />
        <StatCard
          label="Orders"
          value={salesData ? String(salesData.total_orders) : '—'}
          icon={ShoppingBag}
        />
        <StatCard
          label="Suppliers"
          value={totalSuppliers ? String(totalSuppliers) : '—'}
          icon={Users}
        />
        <StatCard
          label="Pending suppliers"
          value={String(pendingSuppliers.length)}
          icon={Store}
          alert={pendingSuppliers.length > 0}
        />
      </div>

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
                  <p className="text-[11px] font-sans text-soil">{s.user_email} · applied {formatDate(s.created_at)}</p>
                </div>
                <Link href="/admin/suppliers" className="text-xs font-sans text-meadow underline-offset-2 hover:underline flex-shrink-0">
                  Review
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

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
                {recentOrders.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-10 text-center text-sm font-sans text-soil">No orders yet.</td>
                  </tr>
                ) : recentOrders.map((o) => (
                  <tr key={o.id} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3.5 font-mono text-xs text-forest">{o.reference}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(o.created_at)}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-forest">{o.buyer_email}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil">
                      {o.sub_orders.map((s) => s.supplier_name).join(', ')}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-forest">£{o.total_amount}</td>
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
