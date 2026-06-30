'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { StatusBadge } from '@/components/supplier/status-badge'
import { SUB_ORDERS, type OrderStatus } from '@/lib/supplier-data'

type FilterTab = 'ALL' | OrderStatus

const TABS: { key: FilterTab; label: string }[] = [
  { key: 'ALL',        label: 'All' },
  { key: 'PENDING',    label: 'Pending' },
  { key: 'CONFIRMED',  label: 'Confirmed' },
  { key: 'DISPATCHED', label: 'Dispatched' },
  { key: 'DELIVERED',  label: 'Delivered' },
  { key: 'CANCELLED',  label: 'Cancelled' },
]

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

export default function OrdersPage() {
  const [filter, setFilter]     = useState<FilterTab>('ALL')
  const [expanded, setExpanded] = useState<string | null>(null)

  const displayed = filter === 'ALL'
    ? SUB_ORDERS
    : SUB_ORDERS.filter((o) => o.status === filter)

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display italic text-2xl text-forest">Orders</h1>
        <p className="text-sm text-soil font-sans mt-0.5">{SUB_ORDERS.length} total orders</p>
      </div>

      {/* Status filter tabs */}
      <div className="border-b border-hoarfrost mb-6 -mx-6 px-6 overflow-x-auto">
        <div className="flex no-scrollbar">
          {TABS.map(({ key, label }) => {
            const count = key === 'ALL'
              ? SUB_ORDERS.length
              : SUB_ORDERS.filter((o) => o.status === key).length
            const active = filter === key
            return (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={[
                  'relative flex-shrink-0 px-4 py-3 text-xs font-sans whitespace-nowrap transition-colors duration-150',
                  active ? 'text-forest font-medium' : 'text-soil hover:text-forest',
                ].join(' ')}
              >
                {label}
                {count > 0 && (
                  <span className={`ml-1.5 font-mono text-[10px] ${active ? 'text-soil' : 'text-hoarfrost'}`}>
                    {count}
                  </span>
                )}
                {active && (
                  <span className="absolute bottom-0 left-4 right-4 h-0.5 bg-forest rounded-full" />
                )}
              </button>
            )
          })}
        </div>
      </div>

      {displayed.length === 0 ? (
        <div className="text-center py-20">
          <p className="font-display italic text-2xl text-hoarfrost">No orders here.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  <th className="w-8 px-4 py-3" />
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Reference</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Date</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden sm:table-cell">Buyer</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden md:table-cell">Items</th>
                  <th className="text-right px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Subtotal</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map((order) => {
                  const isExpanded = expanded === order.id
                  const totalItems = order.items.reduce((s, i) => s + i.quantity, 0)
                  return (
                    <>
                      <tr
                        key={order.id}
                        className="border-b border-hoarfrost hover:bg-mist/50 transition-colors duration-100 cursor-pointer"
                        onClick={() => setExpanded(isExpanded ? null : order.id)}
                      >
                        <td className="px-4 py-3.5">
                          {isExpanded
                            ? <ChevronDown className="w-3.5 h-3.5 text-soil" strokeWidth={1.5} />
                            : <ChevronRight className="w-3.5 h-3.5 text-soil" strokeWidth={1.5} />
                          }
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs text-forest">{order.reference}</td>
                        <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(order.created_at)}</td>
                        <td className="px-4 py-3.5 text-xs font-sans text-forest hidden sm:table-cell">{order.buyer_name}</td>
                        <td className="px-4 py-3.5 text-xs font-sans text-soil hidden md:table-cell">
                          {totalItems} item{totalItems !== 1 ? 's' : ''}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs text-forest text-right">£{order.subtotal}</td>
                        <td className="px-4 py-3.5"><StatusBadge status={order.status} /></td>
                      </tr>

                      {isExpanded && (
                        <tr key={`${order.id}-detail`} className="border-b border-hoarfrost bg-mist/40">
                          <td colSpan={7} className="px-8 py-4">
                            <table className="w-full max-w-lg">
                              <thead>
                                <tr>
                                  <th className="text-left text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium pb-2">Product</th>
                                  <th className="text-left text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium pb-2 hidden sm:table-cell">SKU</th>
                                  <th className="text-right text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium pb-2">Qty</th>
                                  <th className="text-right text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium pb-2">Unit price</th>
                                  <th className="text-right text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium pb-2">Total</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-hoarfrost">
                                {order.items.map((item, i) => (
                                  <tr key={i}>
                                    <td className="py-2 text-xs font-sans text-forest">
                                      {item.product_name}
                                      <span className="text-soil ml-1">· {item.variant_name}</span>
                                    </td>
                                    <td className="py-2 font-mono text-[11px] text-soil hidden sm:table-cell">{item.sku}</td>
                                    <td className="py-2 font-mono text-xs text-forest text-right">{item.quantity}</td>
                                    <td className="py-2 font-mono text-xs text-soil text-right">£{item.unit_price}</td>
                                    <td className="py-2 font-mono text-xs text-forest text-right">
                                      £{(parseFloat(item.unit_price) * item.quantity).toFixed(2)}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
