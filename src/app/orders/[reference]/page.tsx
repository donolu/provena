'use client'

import { use, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, ChevronLeft, XCircle } from 'lucide-react'
import Link from 'next/link'
import { Nav } from '@/components/nav'
import { StatusBadge } from '@/components/supplier/status-badge'
import { getOrder, cancelOrder, raiseDispute } from '@/lib/api/orders'
import { getCart } from '@/lib/api/cart'
import { useAuthStore } from '@/store/auth'
import type { SubOrder } from '@/lib/api/types'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'long', year: 'numeric',
  })
}

const CANCELLABLE = new Set(['PENDING', 'CONFIRMED'])
const DISPUTABLE = new Set(['DISPATCHED', 'DELIVERED'])

const DISPUTE_STATUS_LABEL: Record<string, string> = {
  OPEN: 'Open',
  RESOLVED: 'Resolved',
  REJECTED: 'Rejected',
}

function within7Days(deliveredAt: string | null) {
  if (!deliveredAt) return true
  return Date.now() - new Date(deliveredAt).getTime() < 7 * 24 * 60 * 60 * 1000
}

function SubOrderCard({
  sub,
  reference,
  onDisputeRaised,
}: {
  sub: SubOrder
  reference: string
  onDisputeRaised: () => void
}) {
  const [showForm, setShowForm] = useState(false)
  const [reason, setReason] = useState('')
  const [disputeError, setDisputeError] = useState<string | null>(null)

  const disputeMutation = useMutation({
    mutationFn: () => raiseDispute(reference, sub.id, reason),
    onSuccess: () => {
      setShowForm(false)
      setReason('')
      setDisputeError(null)
      onDisputeRaised()
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setDisputeError(err.response?.data?.detail ?? 'Could not raise dispute.')
    },
  })

  const canDispute =
    DISPUTABLE.has(sub.status) &&
    !sub.disputes.some((d) => d.status === 'OPEN') &&
    (sub.status !== 'DELIVERED' || within7Days(sub.delivered_at))

  return (
    <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
      <div className="px-5 py-3.5 border-b border-hoarfrost flex items-center justify-between">
        <p className="text-xs font-sans font-semibold text-forest">{sub.supplier_name}</p>
        <div className="flex items-center gap-3">
          {sub.tracking_number && (
            <span className="font-mono text-[10px] text-soil">
              Track: {sub.tracking_number}
            </span>
          )}
          <StatusBadge status={sub.status} />
        </div>
      </div>

      <ul className="divide-y divide-hoarfrost">
        {sub.items.map((item) => (
          <li key={item.id} className="px-5 py-3.5 flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-sans font-medium text-forest truncate">{item.product_name}</p>
              <p className="text-xs font-sans text-soil mt-0.5">
                {item.variant_name} · qty {item.quantity}
              </p>
            </div>
            <span className="font-mono text-xs text-forest whitespace-nowrap">£{item.total_price}</span>
          </li>
        ))}
      </ul>

      <div className="px-5 py-3 border-t border-hoarfrost flex items-baseline justify-between">
        <span className="text-xs font-sans text-soil">Subtotal</span>
        <span className="font-mono text-sm font-medium text-forest">£{sub.subtotal}</span>
      </div>

      {sub.disputes.length > 0 && (
        <div className="px-5 py-3 border-t border-hoarfrost space-y-2">
          {sub.disputes.map((d) => (
            <div key={d.id} className="flex items-start gap-2">
              <AlertTriangle
                className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${
                  d.status === 'OPEN' ? 'text-marigold' : d.status === 'RESOLVED' ? 'text-meadow' : 'text-soil'
                }`}
                strokeWidth={1.5}
              />
              <div className="min-w-0">
                <p className="text-[11px] font-sans text-forest font-medium">
                  Dispute {DISPUTE_STATUS_LABEL[d.status]}
                </p>
                <p className="text-[11px] font-sans text-soil mt-0.5 truncate">{d.reason}</p>
                {d.resolution && (
                  <p className="text-[11px] font-sans text-meadow mt-0.5">
                    Resolution: {d.resolution}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {canDispute && !showForm && (
        <div className="px-5 py-3 border-t border-hoarfrost">
          <button
            onClick={() => setShowForm(true)}
            className="text-xs font-sans text-soil hover:text-forest underline-offset-2 hover:underline transition-colors"
          >
            Raise a dispute
          </button>
        </div>
      )}

      {showForm && (
        <div className="px-5 py-4 border-t border-hoarfrost space-y-3">
          <p className="text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">
            Describe the issue
          </p>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="e.g. Items arrived damaged, wrong product received…"
            className="w-full text-xs font-sans border border-hoarfrost rounded px-3 py-2 focus:outline-none focus:border-meadow resize-none"
          />
          {disputeError && (
            <p className="text-xs font-sans text-red-600">{disputeError}</p>
          )}
          <div className="flex items-center gap-3">
            <button
              onClick={() => disputeMutation.mutate()}
              disabled={!reason.trim() || disputeMutation.isPending}
              className="text-xs font-sans text-white bg-forest rounded px-3 py-1.5 hover:bg-meadow disabled:opacity-40 transition-colors"
            >
              Submit dispute
            </button>
            <button
              onClick={() => { setShowForm(false); setReason(''); setDisputeError(null) }}
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

export default function OrderDetailPage({ params }: { params: Promise<{ reference: string }> }) {
  const { reference } = use(params)
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const [cancelError, setCancelError] = useState<string | null>(null)

  const { data: order, isPending } = useQuery({
    queryKey: ['order', reference],
    queryFn: () => getOrder(reference),
    enabled: !!user,
  })

  const cancelMutation = useMutation({
    mutationFn: () => cancelOrder(reference),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['order', reference] })
      qc.invalidateQueries({ queryKey: ['orders'] })
      setCancelError(null)
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setCancelError(err.response?.data?.detail ?? 'Could not cancel order.')
    },
  })

  const { data: cart } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
    enabled: !!user,
  })

  function refreshOrder() {
    qc.invalidateQueries({ queryKey: ['order', reference] })
  }

  return (
    <>
      <Nav cartCount={cart?.item_count ?? 0} onCartClick={() => {}} />

      <main className="max-w-3xl mx-auto px-6 py-10">
        <Link
          href="/orders"
          className="inline-flex items-center gap-1.5 text-xs font-sans text-soil hover:text-forest transition-colors duration-150 mb-8"
        >
          <ChevronLeft className="w-3.5 h-3.5" strokeWidth={1.5} />
          My orders
        </Link>

        {isPending ? (
          <p className="text-sm font-sans text-soil">Loading order…</p>
        ) : !order ? (
          <p className="text-sm font-sans text-soil">Order not found.</p>
        ) : (
          <>
            <div className="flex items-start gap-4 mb-8">
              <CheckCircle2 className="w-7 h-7 text-meadow mt-0.5 flex-shrink-0" strokeWidth={1.5} />
              <div>
                <h1 className="font-display italic text-2xl text-forest">Order {order.reference}</h1>
                <p className="text-sm font-sans text-soil mt-1">
                  Placed {formatDate(order.created_at)}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-sans text-soil">
                Total <span className="font-mono text-forest font-medium">£{order.total_amount}</span>
              </p>
              <div className="flex items-center gap-3">
                <StatusBadge status={order.status} />
                {CANCELLABLE.has(order.status) && (
                  <button
                    onClick={() => {
                      if (confirm('Are you sure you want to cancel this order?')) {
                        cancelMutation.mutate()
                      }
                    }}
                    disabled={cancelMutation.isPending}
                    className="flex items-center gap-1 text-xs font-sans text-red-600 hover:text-red-700 disabled:opacity-40 transition-colors duration-100"
                  >
                    <XCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
                    Cancel order
                  </button>
                )}
              </div>
            </div>
            {cancelError && (
              <p className="text-xs font-sans text-red-600 mt-1">{cancelError}</p>
            )}

            <div className="space-y-4 mt-6">
              {order.sub_orders.map((sub) => (
                <SubOrderCard
                  key={sub.id}
                  sub={sub}
                  reference={reference}
                  onDisputeRaised={refreshOrder}
                />
              ))}
            </div>

            <div className="mt-8 bg-white rounded-lg border border-hoarfrost px-5 py-4">
              <p className="text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium mb-2">Shipping to</p>
              <p className="text-sm font-sans text-forest">{order.shipping_name}</p>
              <p className="text-sm font-sans text-soil">{order.shipping_line1}{order.shipping_line2 ? `, ${order.shipping_line2}` : ''}</p>
              <p className="text-sm font-sans text-soil">{order.shipping_city}, {order.shipping_postcode}</p>
            </div>
          </>
        )}
      </main>
    </>
  )
}
