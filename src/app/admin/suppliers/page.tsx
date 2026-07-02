'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { StatusBadge } from '@/components/supplier/status-badge'
import { Pagination } from '@/components/pagination'
import { getAdminSuppliers, approveSupplier, rejectSupplier } from '@/lib/api/suppliers'
import type { AdminSupplier } from '@/lib/api/types'

type Tab = 'ALL' | 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'REJECTED'

const TABS: { key: Tab; label: string }[] = [
  { key: 'ALL',       label: 'All' },
  { key: 'PENDING',   label: 'Pending' },
  { key: 'ACTIVE',    label: 'Active' },
  { key: 'SUSPENDED', label: 'Suspended' },
  { key: 'REJECTED',  label: 'Rejected' },
]

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function SuppliersPage() {
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('ALL')
  const [page, setPage] = useState(1)
  const [confirming, setConfirming] = useState<{ id: string; action: 'approve' | 'reject' } | null>(null)

  const { data, isPending } = useQuery({
    queryKey: ['admin', 'suppliers', 'all', page],
    queryFn: () => getAdminSuppliers({ page }),
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => approveSupplier(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'suppliers'] }); setConfirming(null) },
  })

  const rejectMutation = useMutation({
    mutationFn: (id: string) => rejectSupplier(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'suppliers'] }); setConfirming(null) },
  })

  const all = data?.results ?? []
  const totalCount = data?.count ?? 0
  const displayed: AdminSupplier[] = tab === 'ALL' ? all : all.filter((s) => s.status === tab)

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display italic text-2xl text-forest">Suppliers</h1>
        <p className="text-sm text-soil font-sans mt-0.5">{totalCount} registered supplier{totalCount !== 1 ? 's' : ''}</p>
      </div>

      <div className="border-b border-hoarfrost mb-6 -mx-6 px-6 overflow-x-auto">
        <div className="flex no-scrollbar">
          {TABS.map(({ key, label }) => {
            const count = key === 'ALL' ? all.length : all.filter((s) => s.status === key).length
            const active = tab === key
            return (
              <button
                key={key}
                onClick={() => setTab(key)}
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
          <div className="px-4 py-12 text-center text-sm font-sans text-soil">Loading suppliers…</div>
        ) : displayed.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm font-sans text-soil">No suppliers in this category.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  {['Business', 'Email', 'Applied', 'Commission', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayed.map((s) => (
                  <>
                    <tr key={s.id} className="border-b border-hoarfrost hover:bg-mist/50 transition-colors duration-100">
                      <td className="px-4 py-3.5">
                        <p className="text-sm font-sans font-medium text-forest">{s.business_name}</p>
                        <p className="text-[10px] font-mono text-hoarfrost">{s.slug}</p>
                      </td>
                      <td className="px-4 py-3.5 text-xs font-sans text-soil">{s.user_email}</td>
                      <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(s.created_at)}</td>
                      <td className="px-4 py-3.5 font-mono text-xs text-forest">{s.commission_rate}%</td>
                      <td className="px-4 py-3.5"><StatusBadge status={s.status} /></td>
                      <td className="px-4 py-3.5">
                        {s.status === 'PENDING' && (
                          <div className="flex gap-3">
                            <button onClick={() => setConfirming({ id: s.id, action: 'approve' })} className="text-xs font-sans text-meadow hover:underline underline-offset-2">Approve</button>
                            <button onClick={() => setConfirming({ id: s.id, action: 'reject' })} className="text-xs font-sans text-soil hover:text-forest hover:underline underline-offset-2">Reject</button>
                          </div>
                        )}
                      </td>
                    </tr>

                    {confirming?.id === s.id && (
                      <tr key={`${s.id}-confirm`} className="border-b border-hoarfrost bg-mist/40">
                        <td colSpan={6} className="px-8 py-4">
                          <div className="flex items-center gap-4">
                            <p className="text-sm font-sans text-forest">
                              {confirming.action === 'approve' ? 'Approve' : 'Reject'}{' '}
                              <span className="font-semibold">{s.business_name}</span>?
                            </p>
                            <button
                              onClick={() => confirming.action === 'approve' ? approveMutation.mutate(s.id) : rejectMutation.mutate(s.id)}
                              disabled={approveMutation.isPending || rejectMutation.isPending}
                              className={`text-xs font-sans font-medium px-3 py-1.5 rounded disabled:opacity-50 ${
                                confirming.action === 'approve' ? 'bg-meadow text-white hover:bg-forest' : 'bg-soil text-white hover:bg-forest'
                              }`}
                            >
                              {approveMutation.isPending || rejectMutation.isPending ? 'Saving…' : 'Confirm'}
                            </button>
                            <button onClick={() => setConfirming(null)} className="text-xs font-sans text-soil hover:text-forest">Cancel</button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} count={totalCount} onChange={(p) => { setPage(p); setConfirming(null) }} />
      </div>
    </div>
  )
}
