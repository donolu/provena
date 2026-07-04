'use client'

import { useQuery } from '@tanstack/react-query'
import { CreditCard, ExternalLink } from 'lucide-react'
import Link from 'next/link'

import { getPayments } from '@/lib/api/orders'

const STATUS_STYLES: Record<string, string> = {
  SUCCEEDED: 'bg-green-100 text-green-800',
  PENDING: 'bg-yellow-100 text-yellow-800',
  FAILED: 'bg-red-100 text-red-800',
  REFUNDED: 'bg-blue-100 text-blue-800',
  PARTIALLY_REFUNDED: 'bg-blue-100 text-blue-800',
}

export default function PaymentHistoryPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['payments'],
    queryFn: () => getPayments(),
  })

  const payments = data?.results ?? []

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-bold text-forest mb-1">Payment history</h1>
      <p className="text-gray-500 text-sm mb-8">All payments made on your account.</p>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-14 bg-gray-100 animate-pulse rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && payments.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <CreditCard className="h-10 w-10 text-gray-300 mb-4" />
          <p className="font-medium text-gray-700">No payments yet</p>
          <p className="text-sm text-gray-500 mt-1">
            Your payment receipts will appear here after your first order.
          </p>
          <Link
            href="/catalogue"
            className="mt-6 rounded-full bg-forest px-5 py-2 text-sm font-medium text-white hover:bg-forest/90"
          >
            Browse products
          </Link>
        </div>
      )}

      {!isLoading && payments.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="px-5 py-3">Order</th>
                <th className="px-5 py-3 text-right">Amount</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 px-5">
              {payments.map((p) => (
                <tr key={p.id} className="border-b last:border-0">
                  <td className="px-5 py-4 pr-4">
                    <Link
                      href={`/orders/${p.order_reference}`}
                      className="font-mono text-sm text-forest hover:underline flex items-center gap-1"
                    >
                      {p.order_reference}
                      <ExternalLink className="h-3 w-3 opacity-60" />
                    </Link>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {new Date(p.created_at).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </p>
                  </td>
                  <td className="px-5 py-4 pr-4 text-right tabular-nums">
                    <span className="font-medium">
                      {p.currency?.toUpperCase() ?? 'GBP'} {Number(p.amount).toFixed(2)}
                    </span>
                    {p.refunded_amount && Number(p.refunded_amount) > 0 && (
                      <p className="text-xs text-blue-600 mt-0.5">
                        -{Number(p.refunded_amount).toFixed(2)} refunded
                      </p>
                    )}
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        STATUS_STYLES[p.status] ?? 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {p.status_display}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
