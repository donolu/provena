'use client'

import { use } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, ChevronLeft } from 'lucide-react'
import Link from 'next/link'
import { Nav } from '@/components/nav'
import { StatusBadge } from '@/components/supplier/status-badge'
import { getOrder } from '@/lib/api/orders'
import { getCart } from '@/lib/api/cart'
import { useAuthStore } from '@/store/auth'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'long', year: 'numeric',
  })
}

export default function OrderDetailPage({ params }: { params: Promise<{ reference: string }> }) {
  const { reference } = use(params)
  const { user } = useAuthStore()

  const { data: order, isPending } = useQuery({
    queryKey: ['order', reference],
    queryFn: () => getOrder(reference),
    enabled: !!user,
  })

  const { data: cart } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
    enabled: !!user,
  })

  return (
    <>
      <Nav cartCount={cart?.item_count ?? 0} onCartClick={() => {}} />

      <main className="max-w-3xl mx-auto px-6 py-10">
        <Link
          href="/catalogue"
          className="inline-flex items-center gap-1.5 text-xs font-sans text-soil hover:text-forest transition-colors duration-150 mb-8"
        >
          <ChevronLeft className="w-3.5 h-3.5" strokeWidth={1.5} />
          Continue shopping
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
                <h1 className="font-display italic text-2xl text-forest">Order confirmed</h1>
                <p className="text-sm font-sans text-soil mt-1">
                  Reference <span className="font-mono text-forest">{order.reference}</span>
                  {' '}· placed {formatDate(order.created_at)}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-sans text-soil">
                Total <span className="font-mono text-forest font-medium">£{order.total_amount}</span>
              </p>
              <StatusBadge status={order.status} />
            </div>

            <div className="space-y-4 mt-6">
              {order.sub_orders.map((sub) => (
                <div key={sub.id} className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
                  <div className="px-5 py-3.5 border-b border-hoarfrost flex items-center justify-between">
                    <p className="text-xs font-sans font-semibold text-forest">{sub.supplier_name}</p>
                    <StatusBadge status={sub.status} />
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
                </div>
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
