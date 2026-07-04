'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Wallet } from 'lucide-react'
import { StatusBadge } from '@/components/supplier/status-badge'
import { Pagination } from '@/components/pagination'
import { getAdminPayouts, processAdminPayout } from '@/lib/api/admin'
import type { Payout } from '@/lib/api/types'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function sumByStatus(payouts: Payout[], status: string) {
  return payouts
    .filter((p) => p.status === status)
    .reduce((s, p) => s + parseFloat(p.net_amount), 0)
    .toFixed(2)
}

export default function AdminPayoutsPage() {
  const [page, setPage] = useState(1)
  const qc = useQueryClient()

  const { data, isPending } = useQuery({
    queryKey: ['admin', 'payouts', page],
    queryFn: () => getAdminPayouts({ page }),
  })

  const processMutation = useMutation({
    mutationFn: (id: string) => processAdminPayout(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'payouts'] }),
  })

  const payouts = data?.results ?? []
  const totalCount = data?.count ?? 0
  const pending    = sumByStatus(payouts, 'PENDING')
  const proc       = sumByStatus(payouts, 'PROCESSING')
  const paid       = sumByStatus(payouts, 'PAID')
  const pendingCount = payouts.filter((p) => p.status === 'PENDING').length

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="font-display italic text-2xl text-forest">Payouts</h1>
          <p className="text-sm text-soil font-sans mt-0.5">Platform payout queue · commission deducted</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-marigold/40 px-4 py-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] uppercase tracking-[0.13em] text-soil font-sans font-medium">Pending</p>
            <Wallet className="w-3.5 h-3.5 text-marigold" strokeWidth={1.5} />
          </div>
          <p className="font-mono text-xl font-medium text-forest">£{pending}</p>
          <p className="text-[11px] text-soil font-sans mt-1">{pendingCount} payout{pendingCount !== 1 ? 's' : ''}</p>
        </div>
        <div className="bg-white rounded-lg border border-hoarfrost px-4 py-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] uppercase tracking-[0.13em] text-soil font-sans font-medium">Processing</p>
            <Wallet className="w-3.5 h-3.5 text-soil" strokeWidth={1.5} />
          </div>
          <p className="font-mono text-xl font-medium text-forest">£{proc}</p>
        </div>
        <div className="bg-white rounded-lg border border-hoarfrost px-4 py-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] uppercase tracking-[0.13em] text-soil font-sans font-medium">Paid out</p>
            <Wallet className="w-3.5 h-3.5 text-meadow" strokeWidth={1.5} />
          </div>
          <p className="font-mono text-xl font-medium text-forest">£{paid}</p>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
        {isPending ? (
          <div className="px-4 py-12 text-center text-sm font-sans text-soil">Loading payouts…</div>
        ) : payouts.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm font-sans text-soil">No payouts yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  {['Supplier', 'Order', 'Gross', 'Fee', 'Net', 'Status', 'Date', ''].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {payouts.map((p) => (
                  <tr key={p.id} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3.5 text-xs font-sans text-forest">{p.supplier_name}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-soil">{p.order_reference}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-soil">£{p.gross_amount}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-soil">£{p.platform_fee}</td>
                    <td className="px-4 py-3.5 font-mono text-xs font-medium text-forest">£{p.net_amount}</td>
                    <td className="px-4 py-3.5"><StatusBadge status={p.status} /></td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(p.created_at)}</td>
                    <td className="px-4 py-3.5">
                      {p.status === 'PENDING' && (
                        <button
                          onClick={() => processMutation.mutate(p.id)}
                          disabled={processMutation.isPending}
                          className="text-xs font-sans text-meadow hover:text-forest transition-colors duration-100 disabled:opacity-40"
                        >
                          Process
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} count={totalCount} onChange={setPage} />
      </div>
    </div>
  )
}
