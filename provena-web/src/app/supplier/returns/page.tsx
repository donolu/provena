'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Pagination } from '@/components/pagination'
import { StatusBadge } from '@/components/supplier/status-badge'
import { getSupplierReturns, supplierApproveReturn, supplierRejectReturn } from '@/lib/api/orders'
import type { OrderReturn, ReturnStatus } from '@/lib/api/types'

type FilterTab = 'ALL' | ReturnStatus

const TABS: { key: FilterTab; label: string }[] = [
  { key: 'ALL',       label: 'All' },
  { key: 'REQUESTED', label: 'Requested' },
  { key: 'APPROVED',  label: 'Approved' },
  { key: 'REJECTED',  label: 'Rejected' },
  { key: 'REFUNDED',  label: 'Refunded' },
]

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function ReturnRow({ ret, onAction }: { ret: OrderReturn; onAction: () => void }) {
  const [mode, setMode] = useState<'idle' | 'approve' | 'reject'>('idle')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const qc = useQueryClient()

  const approveMutation = useMutation({
    mutationFn: () => supplierApproveReturn(ret.id, notes),
    onSuccess: () => {
      setMode('idle')
      setNotes('')
      qc.invalidateQueries({ queryKey: ['supplier', 'returns'] })
      onAction()
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? 'Could not approve return.')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: () => supplierRejectReturn(ret.id, notes),
    onSuccess: () => {
      setMode('idle')
      setNotes('')
      qc.invalidateQueries({ queryKey: ['supplier', 'returns'] })
      onAction()
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? 'Could not reject return.')
    },
  })

  const isPending = approveMutation.isPending || rejectMutation.isPending

  return (
    <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
      <div className="px-5 py-3.5 flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-xs font-sans font-semibold text-forest">
            Order {ret.order_reference}
          </p>
          <p className="text-[11px] font-sans text-soil mt-0.5">
            {ret.raised_by_email} · {formatDate(ret.created_at)}
          </p>
        </div>
        <StatusBadge status={ret.status} />
      </div>

      <div className="px-5 pb-3 border-t border-hoarfrost pt-3">
        <p className="text-xs font-sans text-soil">{ret.reason}</p>
        {ret.supplier_notes && (
          <p className="text-[11px] font-sans text-soil/60 mt-1 italic">{ret.supplier_notes}</p>
        )}
      </div>

      {ret.status === 'REQUESTED' && mode === 'idle' && (
        <div className="px-5 pb-3.5 flex items-center gap-4">
          <button
            onClick={() => { setMode('approve'); setError(null) }}
            className="text-xs font-sans text-meadow hover:text-forest underline-offset-2 hover:underline transition-colors"
          >
            Approve
          </button>
          <button
            onClick={() => { setMode('reject'); setError(null) }}
            className="text-xs font-sans text-red-500 hover:text-red-700 underline-offset-2 hover:underline transition-colors"
          >
            Reject
          </button>
        </div>
      )}

      {mode !== 'idle' && (
        <div className="px-5 pb-4 border-t border-hoarfrost pt-3 space-y-3">
          <p className="text-[10px] uppercase tracking-[0.12em] font-sans font-medium text-soil">
            {mode === 'approve' ? 'Approval notes (optional)' : 'Rejection reason'}
          </p>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder={mode === 'approve' ? 'e.g. Please post item back within 7 days…' : 'e.g. Outside return policy window…'}
            className="w-full text-xs font-sans border border-hoarfrost rounded px-3 py-2 focus:outline-none focus:border-meadow resize-none"
          />
          {error && <p className="text-xs font-sans text-red-600">{error}</p>}
          <div className="flex items-center gap-3">
            <button
              onClick={() => mode === 'approve' ? approveMutation.mutate() : rejectMutation.mutate()}
              disabled={isPending || (mode === 'reject' && !notes.trim())}
              className={`text-xs font-sans text-white rounded px-3 py-1.5 disabled:opacity-40 transition-colors ${
                mode === 'approve' ? 'bg-meadow hover:bg-forest' : 'bg-red-500 hover:bg-red-700'
              }`}
            >
              {mode === 'approve' ? 'Confirm approval' : 'Confirm rejection'}
            </button>
            <button
              onClick={() => { setMode('idle'); setNotes(''); setError(null) }}
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

export default function SupplierReturnsPage() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState<FilterTab>('ALL')
  const [page, setPage] = useState(1)

  const statusParam = filter === 'ALL' ? undefined : filter

  const { data, isPending } = useQuery({
    queryKey: ['supplier', 'returns', filter, page],
    queryFn: () => getSupplierReturns(statusParam, page),
  })

  const returns = data?.results ?? []
  const totalCount = data?.count ?? 0

  function refresh() {
    qc.invalidateQueries({ queryKey: ['supplier', 'returns'] })
  }

  return (
    <div className="px-6 py-8 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display italic text-2xl text-forest">Returns</h1>
        <p className="text-sm text-soil font-sans mt-0.5">{totalCount} return{totalCount !== 1 ? 's' : ''}</p>
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
            <ReturnRow key={ret.id} ret={ret} onAction={refresh} />
          ))}
        </div>
      )}

      {totalCount > 10 && (
        <div className="mt-6">
          <Pagination
            count={totalCount}
            page={page}
            onChange={setPage}
          />
        </div>
      )}
    </div>
  )
}
