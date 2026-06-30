'use client'

import { useState } from 'react'
import { Wallet } from 'lucide-react'
import { StatusBadge } from '@/components/supplier/status-badge'
import { PLATFORM_PAYOUTS, type PlatformPayout, type PayoutStatus } from '@/lib/admin-data'

function sumByStatus(payouts: PlatformPayout[], status: PayoutStatus) {
  return payouts.filter((p) => p.status === status).reduce((s, p) => s + parseFloat(p.net_amount), 0).toFixed(2)
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function AdminPayoutsPage() {
  const [payouts, setPayouts] = useState<PlatformPayout[]>(PLATFORM_PAYOUTS)
  const [processing, setProcessing] = useState<string | null>(null)

  function processPayouts() {
    setProcessing('all')
    setTimeout(() => {
      setPayouts((prev) =>
        prev.map((p) =>
          p.status === 'PENDING' ? { ...p, status: 'PROCESSING' as PayoutStatus } : p,
        ),
      )
      setProcessing(null)
    }, 800)
  }

  const pendingCount = payouts.filter((p) => p.status === 'PENDING').length
  const pending      = sumByStatus(payouts, 'PENDING')
  const proc         = sumByStatus(payouts, 'PROCESSING')
  const paid         = sumByStatus(payouts, 'PAID')

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="font-display italic text-2xl text-forest">Payouts</h1>
          <p className="text-sm text-soil font-sans mt-0.5">Platform payout queue · 10% fee deducted</p>
        </div>
        {pendingCount > 0 && (
          <button
            onClick={processPayouts}
            disabled={processing === 'all'}
            className="flex items-center gap-2 bg-forest text-mist text-xs font-sans font-medium px-4 py-2.5 rounded hover:bg-meadow transition-colors duration-150 disabled:opacity-60"
          >
            <Wallet className="w-3.5 h-3.5" strokeWidth={1.5} />
            {processing === 'all' ? 'Processing…' : `Process ${pendingCount} pending`}
          </button>
        )}
      </div>

      {/* Summary cards */}
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
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-hoarfrost">
                {['Reference', 'Supplier', 'Order', 'Gross', 'Fee (10%)', 'Net', 'Status', 'Date'].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hoarfrost">
              {payouts.map((p) => (
                <tr key={p.id} className="hover:bg-mist/50 transition-colors duration-100">
                  <td className="px-4 py-3.5 font-mono text-xs text-forest">{p.reference}</td>
                  <td className="px-4 py-3.5 text-xs font-sans text-forest">{p.supplier_name}</td>
                  <td className="px-4 py-3.5 font-mono text-xs text-soil">{p.order_reference}</td>
                  <td className="px-4 py-3.5 font-mono text-xs text-soil">£{p.gross_amount}</td>
                  <td className="px-4 py-3.5 font-mono text-xs text-soil">£{p.platform_fee}</td>
                  <td className="px-4 py-3.5 font-mono text-xs font-medium text-forest">£{p.net_amount}</td>
                  <td className="px-4 py-3.5"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(p.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
