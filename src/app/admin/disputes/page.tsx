'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { StatusBadge } from '@/components/supplier/status-badge'
import { getAdminDisputes, adminResolveDispute, adminRejectDispute } from '@/lib/api/orders'
import type { DisputeStatus, OrderDispute } from '@/lib/api/types'

type Tab = 'ALL' | DisputeStatus

const TABS: { key: Tab; label: string }[] = [
  { key: 'ALL',      label: 'All' },
  { key: 'OPEN',     label: 'Open' },
  { key: 'RESOLVED', label: 'Resolved' },
  { key: 'REJECTED', label: 'Rejected' },
]

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function DisputeRow({ dispute }: { dispute: OrderDispute }) {
  const qc = useQueryClient()
  const [action, setAction] = useState<'resolve' | 'reject' | null>(null)
  const [resolution, setResolution] = useState('')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      action === 'resolve'
        ? adminResolveDispute(dispute.id, resolution)
        : adminRejectDispute(dispute.id, resolution),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'disputes'] })
      setAction(null)
      setResolution('')
      setError(null)
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? 'Action failed.')
    },
  })

  return (
    <tr className="hover:bg-mist/50 transition-colors duration-100 align-top">
      <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">
        {formatDate(dispute.created_at)}
      </td>
      <td className="px-4 py-3.5 text-xs font-sans text-forest font-mono">
        {dispute.sub_order_id.slice(0, 8)}…
      </td>
      <td className="px-4 py-3.5 text-xs font-sans text-soil">
        {dispute.raised_by_email ?? '—'}
      </td>
      <td className="px-4 py-3.5 text-xs font-sans text-soil max-w-[220px]">
        <p className="truncate">{dispute.reason}</p>
        {dispute.resolution && (
          <p className="truncate text-meadow mt-0.5">{dispute.resolution}</p>
        )}
      </td>
      <td className="px-4 py-3.5">
        <StatusBadge status={dispute.status} />
      </td>
      <td className="px-4 py-3.5">
        {dispute.status === 'OPEN' ? (
          action ? (
            <div className="space-y-2 min-w-[200px]">
              <textarea
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                rows={2}
                placeholder={action === 'resolve' ? 'Describe the resolution…' : 'Reason for rejection…'}
                className="w-full text-xs font-sans border border-hoarfrost rounded px-2 py-1.5 focus:outline-none focus:border-meadow resize-none"
              />
              {error && <p className="text-[10px] text-red-600">{error}</p>}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => mutation.mutate()}
                  disabled={!resolution.trim() || mutation.isPending}
                  className={`text-xs font-sans text-white rounded px-2.5 py-1 transition-colors disabled:opacity-40 ${
                    action === 'resolve' ? 'bg-meadow hover:bg-forest' : 'bg-red-600 hover:bg-red-700'
                  }`}
                >
                  {action === 'resolve' ? 'Resolve' : 'Reject'}
                </button>
                <button
                  onClick={() => { setAction(null); setResolution(''); setError(null) }}
                  className="text-xs font-sans text-soil hover:text-forest transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <button
                onClick={() => setAction('resolve')}
                className="text-xs font-sans text-meadow hover:text-forest transition-colors"
              >
                Resolve
              </button>
              <button
                onClick={() => setAction('reject')}
                className="text-xs font-sans text-red-600 hover:text-red-700 transition-colors"
              >
                Reject
              </button>
            </div>
          )
        ) : null}
      </td>
    </tr>
  )
}

export default function AdminDisputesPage() {
  const [filter, setFilter] = useState<Tab>('ALL')

  const { data: disputes = [], isPending } = useQuery({
    queryKey: ['admin', 'disputes'],
    queryFn: () => getAdminDisputes(),
  })

  const displayed = filter === 'ALL' ? disputes : disputes.filter((d) => d.status === filter)

  const openCount = disputes.filter((d) => d.status === 'OPEN').length

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display italic text-2xl text-forest">Disputes</h1>
        <p className="text-sm text-soil font-sans mt-0.5">
          {openCount > 0 ? (
            <>{openCount} open dispute{openCount !== 1 ? 's' : ''} awaiting mediation</>
          ) : (
            'No open disputes'
          )}
        </p>
      </div>

      <div className="border-b border-hoarfrost mb-6 -mx-6 px-6 overflow-x-auto">
        <div className="flex no-scrollbar">
          {TABS.map(({ key, label }) => {
            const count = key === 'ALL' ? disputes.length : disputes.filter((d) => d.status === key).length
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
          <div className="px-4 py-12 text-center text-sm font-sans text-soil">Loading disputes…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  {['Raised', 'Sub-order', 'Buyer', 'Reason / Resolution', 'Status', ''].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {displayed.map((d) => (
                  <DisputeRow key={d.id} dispute={d} />
                ))}
                {displayed.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-sm font-sans text-soil">
                      No disputes in this category.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
