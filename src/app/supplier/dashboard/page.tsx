'use client'

import Link from 'next/link'
import { BarChart2, Package, ShoppingBag, AlertTriangle, Wallet } from 'lucide-react'
import { StatCard } from '@/components/supplier/stat-card'
import { StatusBadge } from '@/components/supplier/status-badge'
import {
  SUPPLIER_STATS,
  SUPPLIER_PRODUCTS,
  SUB_ORDERS,
  trend,
} from '@/lib/supplier-data'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

export default function DashboardPage() {
  const revenueTrend = trend(
    parseFloat(SUPPLIER_STATS.revenue_30d),
    parseFloat(SUPPLIER_STATS.revenue_prev_30d),
  )
  const ordersTrend = trend(SUPPLIER_STATS.orders_30d, SUPPLIER_STATS.orders_prev_30d)

  const recentOrders  = SUB_ORDERS.slice(0, 5)
  const lowStockItems = SUPPLIER_PRODUCTS.filter(
    (p) => p.stock_available > 0 && p.stock_available <= p.low_stock_threshold,
  )
  const outOfStock = SUPPLIER_PRODUCTS.filter((p) => p.stock_available === 0)

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display italic text-2xl text-forest">Overview</h1>
        <p className="text-sm text-soil font-sans mt-0.5">Last 30 days</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <StatCard
          label="Revenue"
          prefix="£"
          value={SUPPLIER_STATS.revenue_30d}
          icon={BarChart2}
          trend={{ pct: revenueTrend, label: 'vs prev 30d' }}
        />
        <StatCard
          label="Orders"
          value={String(SUPPLIER_STATS.orders_30d)}
          icon={ShoppingBag}
          trend={{ pct: ordersTrend, label: 'vs prev 30d' }}
        />
        <StatCard
          label="Pending payout"
          prefix="£"
          value={SUPPLIER_STATS.pending_payout}
          icon={Wallet}
        />
        <StatCard
          label="Low stock"
          value={String(SUPPLIER_STATS.low_stock_count)}
          suffix="item"
          icon={AlertTriangle}
          alert={SUPPLIER_STATS.low_stock_count > 0}
        />
      </div>

      {/* Alerts row */}
      {(lowStockItems.length > 0 || outOfStock.length > 0) && (
        <div className="mb-8 space-y-2">
          {lowStockItems.map((p) => (
            <div key={p.id} className="flex items-center justify-between bg-marigold/8 border border-marigold/30 rounded-lg px-4 py-3">
              <div className="flex items-center gap-2.5">
                <AlertTriangle className="w-3.5 h-3.5 text-marigold flex-shrink-0" strokeWidth={1.5} />
                <p className="text-sm font-sans text-forest">
                  <span className="font-medium">{p.name}</span>
                  {' '}— only <span className="font-mono">{p.stock_available}</span> units left
                  <span className="text-soil"> (threshold: {p.low_stock_threshold})</span>
                </p>
              </div>
              <Link href="/supplier/products" className="text-xs font-sans text-meadow underline-offset-2 hover:underline">
                Update stock
              </Link>
            </div>
          ))}
          {outOfStock.map((p) => (
            <div key={p.id} className="flex items-center justify-between bg-soil/5 border border-soil/20 rounded-lg px-4 py-3">
              <p className="text-sm font-sans text-forest">
                <span className="font-medium">{p.name}</span> is <span className="text-soil">out of stock</span>
              </p>
              <Link href="/supplier/products" className="text-xs font-sans text-meadow underline-offset-2 hover:underline">
                Restock
              </Link>
            </div>
          ))}
        </div>
      )}

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
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Reference</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Date</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Buyer</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Items</th>
                  <th className="text-right px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Subtotal</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {recentOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3.5 font-mono text-xs text-forest">{order.reference}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(order.created_at)}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-forest">{order.buyer_name}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil">
                      {order.items.reduce((s, i) => s + i.quantity, 0)} item{order.items.reduce((s, i) => s + i.quantity, 0) !== 1 ? 's' : ''}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-forest text-right">£{order.subtotal}</td>
                    <td className="px-4 py-3.5"><StatusBadge status={order.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Products quick view */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-sans font-semibold text-forest">Your products</h2>
          <Link href="/supplier/products" className="text-xs font-sans text-meadow underline-offset-2 hover:underline">
            Manage all
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {SUPPLIER_PRODUCTS.map((p) => {
            const isLow = p.stock_available > 0 && p.stock_available <= p.low_stock_threshold
            const isOut = p.stock_available === 0
            return (
              <div key={p.id} className="bg-white rounded-lg border border-hoarfrost px-4 py-3.5 flex items-center justify-between">
                <div>
                  <p className="text-sm font-sans font-medium text-forest">{p.name}</p>
                  <p className="font-mono text-[11px] text-soil mt-0.5">{p.sku}</p>
                </div>
                <div className="text-right">
                  <p className={`font-mono text-xs font-medium ${isOut ? 'text-soil' : isLow ? 'text-marigold' : 'text-meadow'}`}>
                    {isOut ? 'Out of stock' : `${p.stock_available} left`}
                  </p>
                  <p className="font-mono text-xs text-forest mt-0.5">£{p.price}/{p.unit}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
