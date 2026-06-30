'use client'

import { Wallet } from 'lucide-react'
import { StatusBadge } from '@/components/supplier/status-badge'
import { PAYOUTS } from '@/lib/supplier-data'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function sumByStatus(status: string) {
  return PAYOUTS
    .filter((p) => p.status === status)
    .reduce((s, p) => s + parseFloat(p.net_amount), 0)
    .toFixed(2)
}

export default function PayoutsPage() {
  const pending    = sumByStatus('PENDING')
  const processing = sumByStatus('PROCESSING')
  const paid       = sumByStatus('PAID')

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display italic text-2xl text-forest">Payouts</h1>
        <p className="text-sm text-soil font-sans mt-0.5">Net amounts after the platform fee (10%)</p>
      </div>

      {/* Summary cards */}
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

      {/* Payout history table */}
      <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-hoarfrost">
                <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Reference</th>
                <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden sm:table-cell">Order</th>
                <th className="text-right px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden md:table-cell">Gross</th>
                <th className="text-right px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden md:table-cell">Fee</th>
                <th className="text-right px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Net</th>
                <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Status</th>
                <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden lg:table-cell">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hoarfrost">
              {PAYOUTS.map((payout) => (
                <tr key={payout.id} className="hover:bg-mist/50 transition-colors duration-100">
                  <td className="px-4 py-3.5 font-mono text-xs text-forest">{payout.reference}</td>
                  <td className="px-4 py-3.5 font-mono text-xs text-soil hidden sm:table-cell">{payout.order_reference}</td>
                  <td className="px-4 py-3.5 font-mono text-xs text-soil text-right hidden md:table-cell">£{payout.gross_amount}</td>
                  <td className="px-4 py-3.5 font-mono text-xs text-soil text-right hidden md:table-cell">£{payout.platform_fee}</td>
                  <td className="px-4 py-3.5 font-mono text-xs font-medium text-forest text-right">£{payout.net_amount}</td>
                  <td className="px-4 py-3.5"><StatusBadge status={payout.status} /></td>
                  <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap hidden lg:table-cell">
                    {payout.paid_at ? formatDate(payout.paid_at) : formatDate(payout.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
