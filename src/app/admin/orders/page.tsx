'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { StatusBadge } from '@/components/supplier/status-badge'
import { Pagination } from '@/components/pagination'
import { getAdminOrders, adminRefundPayment } from '@/lib/api/orders'
import type { Order, OrderStatus } from '@/lib/api/types'

type Tab = 'ALL' | OrderStatus

const TABS: { key: Tab; label: string }[] = [
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

const REFUNDABLE_PAYMENT = new Set(['SUCCEEDED', 'PARTIAL_REFUND'])

export default function AdminOrdersPage() {
  const [filter, setFilter] = useState<Tab>('ALL')
  const [page, setPage] = useState(1)
  const [refundTarget, setRefundTarget] = useState<{ paymentId: string; max: number } | null>(null)
  const [refundAmount, setRefundAmount] = useState('')
  const qc = useQueryClient()

  const { data, isPending } = useQuery({
    queryKey: ['admin', 'orders', page],
    queryFn: () => getAdminOrders(page),
  })

  const refundMutation = useMutation({
    mutationFn: ({ paymentId, amount }: { paymentId: string; amount?: number }) =>
      adminRefundPayment(paymentId, amount),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'orders'] })
      setRefundTarget(null)
      setRefundAmount('')
    },
  })

  const all: Order[] = data?.results ?? []
  const totalCount = data?.count ?? 0
  const displayed = filter === 'ALL' ? all : all.filter((o) => o.status === filter)

  const totalRevenue = displayed
    .filter((o) => o.status !== 'CANCELLED')
    .reduce((s, o) => s + parseFloat(o.total_amount), 0)
    .toFixed(2)

  function handleRefundSubmit() {
    if (!refundTarget) return
    const amount = refundAmount ? parseFloat(refundAmount) : undefined
    if (amount !== undefined && (isNaN(amount) || amount <= 0 || amount > refundTarget.max)) return
    refundMutation.mutate({ paymentId: refundTarget.paymentId, amount })
  }

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-display italic text-2xl text-forest">Orders</h1>
          <p className="text-sm text-soil font-sans mt-0.5">
            {displayed.length} order{displayed.length !== 1 ? 's' : ''}
            {filter !== 'ALL' && filter !== 'CANCELLED' && (
              <> · <span className="font-mono text-forest">£{totalRevenue}</span> total</>
            )}
          </p>
        </div>
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
                  <span className={`ml-1.5 font-mono text-[10px] ${active ? 'text-soil' : 'text-hoarfrost'}`}>{count}</span>
                )}
                {active && <span className="absolute bottom-0 left-4 right-4 h-0.5 bg-forest rounded-full" />}
              </button>
            )
          })}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
        {isPending ? (
          <div className="px-4 py-12 text-center text-sm font-sans text-soil">Loading orders…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  {['Reference', 'Date', 'Buyer', 'Suppliers', 'Total', 'Status', ''].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {displayed.map((o) => (
                  <tr key={o.id} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3.5 font-mono text-xs text-forest">{o.reference}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(o.created_at)}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-forest">{o.buyer_email}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil">
                      {o.sub_orders.map((s) => s.supplier_name).join(', ')}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-forest">£{o.total_amount}</td>
                    <td className="px-4 py-3.5"><StatusBadge status={o.status} /></td>
                    <td className="px-4 py-3.5">
                      {o.payment_id && o.payment_status && REFUNDABLE_PAYMENT.has(o.payment_status) && (
                        refundTarget?.paymentId === o.payment_id ? (
                          <div className="flex items-center gap-2">
                            <div className="relative">
                              <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-soil">£</span>
                              <input
                                type="number"
                                min="0.01"
                                step="0.01"
                                max={refundTarget.max}
                                placeholder={String(refundTarget.max)}
                                value={refundAmount}
                                onChange={(e) => setRefundAmount(e.target.value)}
                                className="pl-4 pr-2 py-1 w-20 text-xs font-mono border border-hoarfrost rounded focus:outline-none focus:border-meadow"
                              />
                            </div>
                            <button
                              onClick={() => handleRefundSubmit()}
                              disabled={refundMutation.isPending}
                              className="text-xs font-sans text-red-600 hover:text-red-700 disabled:opacity-40 transition-colors"
                            >
                              {refundAmount ? 'Partial' : 'Full'}
                            </button>
                            <button
                              onClick={() => { setRefundTarget(null); setRefundAmount('') }}
                              className="text-xs font-sans text-soil hover:text-forest transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              const max = parseFloat(o.total_amount) - parseFloat(o.refunded_amount ?? '0')
                              setRefundTarget({ paymentId: o.payment_id!, max })
                              setRefundAmount('')
                            }}
                            className="text-xs font-sans text-red-600 hover:text-red-700 transition-colors"
                          >
                            Refund
                          </button>
                        )
                      )}
                    </td>
                  </tr>
                ))}
                {displayed.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-sm font-sans text-soil">No orders in this category.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} count={totalCount} onChange={setPage} />
      </div>
    </div>
  )
}
