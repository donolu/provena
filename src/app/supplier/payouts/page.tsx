'use client'

import { useQuery } from '@tanstack/react-query'
import { Wallet } from 'lucide-react'
import { StatusBadge } from '@/components/supplier/status-badge'
import { getSupplierPayouts } from '@/lib/api/admin'
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

export default function PayoutsPage() {
  const { data, isPending } = useQuery({
    queryKey: ['supplier', 'payouts'],
    queryFn: getSupplierPayouts,
  })

  const payouts = data?.results ?? []
  const pending    = sumByStatus(payouts, 'PENDING')
  const processing = sumByStatus(payouts, 'PROCESSING')
  const paid       = sumByStatus(payouts, 'PAID')

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display italic text-2xl text-forest">Payouts</h1>
        <p className="text-sm text-soil font-sans mt-0.5">Net amounts after the platform fee</p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-10">
        <div className="bg-white rounded-lg border border-hoarfrost px-4 py-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] uppercase tracking-[0.13em] text-soil font-sans font-medium">Pending</p>
            <Wallet className="w-3.5 h-3.5 text-marigold" strokeWidth={1.5} />
          </div>
          <p className="font-mono text-xl font-medium text-forest">£{pending}</p>
        </div>
        <div className="bg-white rounded-lg border border-hoarfrost px-4 py-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] uppercase tracking-[0.13em] text-soil font-sans font-medium">Processing</p>
            <Wallet className="w-3.5 h-3.5 text-soil" strokeWidth={1.5} />
          </div>
          <p className="font-mono text-xl font-medium text-forest">£{processing}</p>
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
                  {['Order', 'Gross', 'Fee', 'Net', 'Status', 'Date'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {payouts.map((payout) => (
                  <tr key={payout.id} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3.5 font-mono text-xs text-soil">{payout.order_reference}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-soil">£{payout.gross_amount}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-soil">£{payout.platform_fee}</td>
                    <td className="px-4 py-3.5 font-mono text-xs font-medium text-forest">£{payout.net_amount}</td>
                    <td className="px-4 py-3.5"><StatusBadge status={payout.status} /></td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">
                      {formatDate(payout.updated_at || payout.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
