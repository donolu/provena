'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { StatusBadge } from '@/components/supplier/status-badge'
import { Pagination } from '@/components/pagination'
import { getSupplierSubOrders, confirmSubOrder, dispatchSubOrder } from '@/lib/api/orders'
import type { OrderStatus } from '@/lib/api/types'

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
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function OrdersPage() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState<FilterTab>('ALL')
  const [page, setPage] = useState(1)
  const [dispatching, setDispatching] = useState<string | null>(null)
  const [trackingInput, setTrackingInput] = useState('')

  const { data, isPending } = useQuery({
    queryKey: ['supplier', 'suborders', page],
    queryFn: () => getSupplierSubOrders(page),
  })

  const confirmMutation = useMutation({
    mutationFn: (id: string) => confirmSubOrder(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['supplier', 'suborders'] }),
  })

  const dispatchMutation = useMutation({
    mutationFn: ({ id, tracking }: { id: string; tracking: string }) =>
      dispatchSubOrder(id, tracking),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['supplier', 'suborders'] })
      setDispatching(null)
      setTrackingInput('')
    },
  })

  const all = data?.results ?? []
  const totalCount = data?.count ?? 0
  const displayed = filter === 'ALL' ? all : all.filter((o) => o.status === filter)

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display italic text-2xl text-forest">Orders</h1>
        <p className="text-sm text-soil font-sans mt-0.5">{all.length} total order{all.length !== 1 ? 's' : ''}</p>
      </div>

      <div className="border-b border-hoarfrost mb-6 -mx-6 px-6 overflow-x-auto">
        <div className="flex no-scrollbar">
          {TABS.map(({ key, label }) => {
            const count = key === 'ALL' ? all.length : all.filter((o) => o.status === key).length
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
                {active && <span className="absolute bottom-0 left-4 right-4 h-0.5 bg-forest rounded-full" />}
              </button>
            )
          })}
        </div>
      </div>

      {isPending ? (
        <div className="text-center py-20">
          <p className="font-display italic text-2xl text-hoarfrost">Loading…</p>
        </div>
      ) : displayed.length === 0 ? (
        <div className="text-center py-20">
          <p className="font-display italic text-2xl text-hoarfrost">No orders here.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Reference</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Date</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden sm:table-cell">Buyer</th>
                  <th className="text-right px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Subtotal</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Status</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map((order) => (
                  <>
                    <tr
                      key={order.id}
                      className="border-b border-hoarfrost hover:bg-mist/50 transition-colors duration-100"
                    >
                      <td className="px-4 py-3.5 font-mono text-xs text-forest">{order.order_reference}</td>
                      <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(order.created_at)}</td>
                      <td className="px-4 py-3.5 text-xs font-sans text-forest hidden sm:table-cell">{order.buyer_email}</td>
                      <td className="px-4 py-3.5 font-mono text-xs text-forest text-right">£{order.subtotal}</td>
                      <td className="px-4 py-3.5"><StatusBadge status={order.status} /></td>
                      <td className="px-4 py-3.5">
                        {order.status === 'PENDING' && (
                          <button
                            onClick={() => confirmMutation.mutate(order.id)}
                            disabled={confirmMutation.isPending}
                            className="text-xs font-sans text-meadow underline-offset-2 hover:underline disabled:opacity-50"
                          >
                            Confirm
                          </button>
                        )}
                        {order.status === 'CONFIRMED' && (
                          <button
                            onClick={() => setDispatching(order.id)}
                            className="text-xs font-sans text-meadow underline-offset-2 hover:underline"
                          >
                            Dispatch
                          </button>
                        )}
                      </td>
                    </tr>

                    {dispatching === order.id && (
                      <tr key={`${order.id}-dispatch`} className="border-b border-hoarfrost bg-mist/40">
                        <td colSpan={6} className="px-8 py-4">
                          <div className="flex items-center gap-3 max-w-sm">
                            <input
                              type="text"
                              placeholder="Tracking number (optional)"
                              value={trackingInput}
                              onChange={(e) => setTrackingInput(e.target.value)}
                              className="flex-1 border border-hoarfrost rounded px-3 py-1.5 text-xs font-mono text-forest bg-white focus:outline-none focus:border-forest"
                            />
                            <button
                              onClick={() => dispatchMutation.mutate({ id: order.id, tracking: trackingInput })}
                              disabled={dispatchMutation.isPending}
                              className="text-xs font-sans font-medium bg-forest text-mist px-3 py-1.5 rounded hover:bg-meadow transition-colors duration-150 disabled:opacity-50"
                            >
                              {dispatchMutation.isPending ? 'Saving…' : 'Mark dispatched'}
                            </button>
                            <button
                              onClick={() => { setDispatching(null); setTrackingInput('') }}
                              className="text-xs font-sans text-soil hover:text-forest"
                            >
                              Cancel
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        <Pagination page={page} count={totalCount} onChange={(p) => { setPage(p); setDispatching(null) }} />
        </div>
      )}
    </div>
  )
}
