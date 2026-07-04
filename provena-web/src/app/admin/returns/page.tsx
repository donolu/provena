'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Pagination } from '@/components/pagination'
import { StatusBadge } from '@/components/supplier/status-badge'
import { getAdminReturns, adminProcessReturnRefund } from '@/lib/api/orders'
import type { OrderReturn, ReturnStatus } from '@/lib/api/types'

type Tab = 'ALL' | ReturnStatus

const TABS: { key: Tab; label: string }[] = [
  { key: 'ALL',       label: 'All' },
  { key: 'REQUESTED', label: 'Requested' },
  { key: 'APPROVED',  label: 'Approved' },
  { key: 'REJECTED',  label: 'Rejected' },
  { key: 'REFUNDED',  label: 'Refunded' },
]

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function ReturnRow({ ret }: { ret: OrderReturn }) {
  const qc = useQueryClient()
  const [showRefund, setShowRefund] = useState(false)
  const [amountStr, setAmountStr] = useState('')
  const [error, setError] = useState<string | null>(null)

  const refundMutation = useMutation({
    mutationFn: () => {
      const amount = amountStr ? parseFloat(amountStr) : undefined
      return adminProcessReturnRefund(ret.id, amount)
    },
    onSuccess: () => {
      setShowRefund(false)
      setAmountStr('')
      setError(null)
      qc.invalidateQueries({ queryKey: ['admin', 'returns'] })
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? 'Could not process refund.')
    },
  })

  return (
    <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
      <div className="px-5 py-3.5 flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-xs font-sans font-semibold text-forest">
            Order {ret.order_reference}
          </p>
          <p className="text-[11px] font-sans text-soil mt-0.5">
            {ret.supplier_name} · {ret.raised_by_email ?? 'unknown buyer'} · {formatDate(ret.created_at)}
          </p>
        </div>
        <StatusBadge status={ret.status} />
      </div>

      <div className="px-5 pb-3 border-t border-hoarfrost pt-3 space-y-1">
        <p className="text-xs font-sans text-soil">{ret.reason}</p>
        {ret.supplier_notes && (
          <p className="text-[11px] font-sans text-soil/60 italic">Supplier: {ret.supplier_notes}</p>
        )}
        {ret.refund_amount && (
          <p className="text-[11px] font-mono text-forest">Refunded: £{ret.refund_amount}</p>
        )}
      </div>

      {ret.status === 'APPROVED' && !showRefund && (
        <div className="px-5 pb-3.5">
          <button
            onClick={() => { setShowRefund(true); setError(null) }}
            className="text-xs font-sans text-meadow hover:text-forest underline-offset-2 hover:underline transition-colors"
          >
            Process refund
          </button>
        </div>
      )}

      {showRefund && (
        <div className="px-5 pb-4 border-t border-hoarfrost pt-3 space-y-3">
          <p className="text-[10px] uppercase tracking-[0.12em] font-sans font-medium text-soil">
            Refund amount (leave blank for full refund)
          </p>
          <input
            type="number"
            value={amountStr}
            onChange={(e) => setAmountStr(e.target.value)}
            placeholder="e.g. 3.99"
            step="0.01"
            min="0.01"
            className="w-40 text-xs font-mono border border-hoarfrost rounded px-3 py-2 focus:outline-none focus:border-meadow"
          />
          {error && <p className="text-xs font-sans text-red-600">{error}</p>}
          <div className="flex items-center gap-3">
            <button
              onClick={() => refundMutation.mutate()}
              disabled={refundMutation.isPending}
              className="text-xs font-sans text-white bg-forest rounded px-3 py-1.5 hover:bg-meadow disabled:opacity-40 transition-colors"
            >
              {refundMutation.isPending ? 'Processing…' : 'Confirm refund'}
            </button>
            <button
              onClick={() => { setShowRefund(false); setAmountStr(''); setError(null) }}
              className="text-xs font-sans text-soil hover:text-forest transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function AdminReturnsPage() {
  const [filter, setFilter] = useState<Tab>('ALL')
  const [page, setPage] = useState(1)

  const statusParam = filter === 'ALL' ? undefined : filter

  const { data, isPending } = useQuery({
    queryKey: ['admin', 'returns', filter, page],
    queryFn: () => getAdminReturns(statusParam, page),
  })

  const returns = data?.results ?? []
  const totalCount = data?.count ?? 0
  const approvedCount = filter === 'ALL'
    ? returns.filter((r) => r.status === 'APPROVED').length
    : 0

  return (
    <div className="px-6 py-8 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display italic text-2xl text-forest">Returns</h1>
        <p className="text-sm text-soil font-sans mt-0.5">
          {totalCount} return{totalCount !== 1 ? 's' : ''}
          {approvedCount > 0 && ` · ${approvedCount} awaiting refund`}
        </p>
      </div>

      <div className="flex items-center gap-1 mb-6 flex-wrap">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setFilter(tab.key); setPage(1) }}
            className={`px-3 py-1.5 text-xs font-sans rounded-full border transition-colors ${
              filter === tab.key
                ? 'bg-forest text-white border-forest'
                : 'bg-white text-soil border-hoarfrost hover:border-forest hover:text-forest'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isPending ? (
        <p className="text-sm font-sans text-soil">Loading…</p>
      ) : returns.length === 0 ? (
        <p className="text-sm font-sans text-soil">No returns found.</p>
      ) : (
        <div className="space-y-3">
          {returns.map((ret) => (
            <ReturnRow key={ret.id} ret={ret} />
          ))}
        </div>
      )}

      {totalCount > 10 && (
        <div className="mt-6">
          <Pagination count={totalCount} page={page} onChange={setPage} />
        </div>
      )}
    </div>
  )
}
