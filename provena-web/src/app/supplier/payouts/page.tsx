'use client'

import { Suspense, useState, useTransition } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { Wallet, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react'
import { StatusBadge } from '@/components/supplier/status-badge'
import { Pagination } from '@/components/pagination'
import { getSupplierPayouts } from '@/lib/api/admin'
import { getMySupplierProfile, getStripeConnectUrl } from '@/lib/api/suppliers'
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

function StripeConnectBanner({ onboardingComplete }: { onboardingComplete: boolean }) {
  const [isPending, startTransition] = useTransition()

  function handleConnect() {
    startTransition(async () => {
      const url = await getStripeConnectUrl()
      if (url) window.location.href = url
    })
  }

  if (onboardingComplete) {
    return (
      <div className="flex items-center gap-2.5 mb-8 px-4 py-3 bg-meadow/10 border border-meadow/30 rounded-lg">
        <CheckCircle className="w-4 h-4 text-meadow shrink-0" strokeWidth={1.5} />
        <p className="text-sm font-sans text-forest">
          Stripe account connected. Payouts will be transferred automatically once processed.
        </p>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 mb-8 px-4 py-4 bg-marigold/10 border border-marigold/40 rounded-lg">
      <AlertCircle className="w-4 h-4 text-marigold shrink-0 mt-0.5" strokeWidth={1.5} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-sans text-forest font-medium">Connect your Stripe account to receive payouts</p>
        <p className="text-xs font-sans text-soil mt-0.5">
          You need to complete Stripe onboarding before we can transfer earnings to you.
        </p>
      </div>
      <button
        onClick={handleConnect}
        disabled={isPending}
        className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-forest text-white text-xs font-sans font-medium rounded-md hover:bg-forest/90 disabled:opacity-60 transition-colors"
      >
        {isPending ? 'Redirecting…' : 'Connect Stripe'}
        {!isPending && <ExternalLink className="w-3 h-3" strokeWidth={1.5} />}
      </button>
    </div>
  )
}

function PayoutsContent() {
  const [page, setPage] = useState(1)
  const searchParams = useSearchParams()
  const justConnected = searchParams.get('connected') === '1'

  const { data, isPending } = useQuery({
    queryKey: ['supplier', 'payouts', page],
    queryFn: () => getSupplierPayouts(page),
  })

  const { data: profile } = useQuery({
    queryKey: ['supplier', 'profile'],
    queryFn: getMySupplierProfile,
  })

  const payouts = data?.results ?? []
  const totalCount = data?.count ?? 0
  const pending    = sumByStatus(payouts, 'PENDING')
  const processing = sumByStatus(payouts, 'PROCESSING')
  const paid       = sumByStatus(payouts, 'PAID')

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display italic text-2xl text-forest">Payouts</h1>
        <p className="text-sm text-soil font-sans mt-0.5">Net amounts after the platform fee</p>
      </div>

      {justConnected && (
        <div className="flex items-center gap-2.5 mb-6 px-4 py-3 bg-meadow/10 border border-meadow/30 rounded-lg">
          <CheckCircle className="w-4 h-4 text-meadow shrink-0" strokeWidth={1.5} />
          <p className="text-sm font-sans text-forest">
            Stripe onboarding complete. Your account is being verified — this can take a few minutes.
          </p>
        </div>
      )}

      {profile && (
        <StripeConnectBanner onboardingComplete={profile.stripe_onboarding_complete} />
      )}

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
        <Pagination page={page} count={totalCount} onChange={setPage} />
      </div>
    </div>
  )
}

export default function PayoutsPage() {
  return (
    <Suspense fallback={null}>
      <PayoutsContent />
    </Suspense>
  )
}
