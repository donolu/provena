'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, Package } from 'lucide-react'
import Link from 'next/link'
import { loadStripe } from '@stripe/stripe-js'
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js'
import { Nav } from '@/components/nav'
import { OrderBreakdown } from '@/components/order-breakdown'
import { getCart, clearCart } from '@/lib/api/cart'
import { placeOrder, createPaymentIntent } from '@/lib/api/orders'
import { getAddresses } from '@/lib/api/addresses'
import type { Address } from '@/lib/api/addresses'
import { useAuthStore } from '@/store/auth'
import type { Order } from '@/lib/api/types'

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!)

interface ShippingForm {
  name: string
  line1: string
  line2: string
  city: string
  postcode: string
  country: string
  notes: string
}

const EMPTY: ShippingForm = {
  name: '', line1: '', line2: '', city: '', postcode: '', country: 'GB', notes: '',
}

function Field({
  label, name, value, onChange, required = true, placeholder = '',
}: {
  label: string; name: keyof ShippingForm; value: string
  onChange: (v: string) => void; required?: boolean; placeholder?: string
}) {
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium mb-1.5">
        {label}{required && <span className="text-terracotta ml-0.5">*</span>}
      </label>
      <input
        type="text"
        name={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150"
      />
    </div>
  )
}

function OrderSummary({ items, total }: { items: { id: string; product_name: string; variant_name: string; quantity: number; subtotal: string }[]; total: string }) {
  return (
    <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
      <div className="px-5 py-4 border-b border-hoarfrost">
        <h2 className="text-sm font-sans font-semibold text-forest">Order summary</h2>
        <p className="text-xs font-sans text-soil mt-0.5">{items.length} item{items.length !== 1 ? 's' : ''}</p>
      </div>
      <ul className="divide-y divide-hoarfrost">
        {items.map((item) => (
          <li key={item.id} className="px-5 py-3.5 flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-sans font-medium text-forest truncate">{item.product_name}</p>
              <p className="text-xs font-sans text-soil mt-0.5">{item.variant_name} · qty {item.quantity}</p>
            </div>
            <span className="font-mono text-xs text-forest whitespace-nowrap">£{item.subtotal}</span>
          </li>
        ))}
      </ul>
      <div className="px-5 py-4 border-t border-hoarfrost flex items-baseline justify-between">
        <span className="text-sm font-sans text-soil">Subtotal</span>
        <span className="font-mono text-base font-semibold text-forest">£{total}</span>
      </div>
      <p className="px-5 pb-4 -mt-2 text-[11px] font-sans text-soil">Excl. shipping &amp; VAT</p>
    </div>
  )
}

function PaymentStep({
  order,
  onSuccess,
}: {
  order: Order
  onSuccess: () => void
}) {
  const stripe = useStripe()
  const elements = useElements()
  const [error, setError] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)

  async function handlePay(e: React.FormEvent) {
    e.preventDefault()
    if (!stripe || !elements) return
    setProcessing(true)
    setError(null)

    const result = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/orders/${order.reference}`,
      },
      redirect: 'if_required',
    })

    if (result.error) {
      setError(result.error.message ?? 'Payment failed. Please try again.')
      setProcessing(false)
    } else {
      onSuccess()
    }
  }

  return (
    <form onSubmit={handlePay} className="space-y-5">
      <h2 className="text-sm font-sans font-semibold text-forest">Payment</h2>
      <p className="text-xs font-sans text-soil">Order {order.reference}</p>

      <div className="bg-white border border-hoarfrost rounded p-4">
        <OrderBreakdown order={order} />
      </div>

      <div className="bg-white border border-hoarfrost rounded p-4">
        <PaymentElement />
      </div>

      {error && (
        <p className="text-xs font-sans text-terracotta bg-terracotta/5 border border-terracotta/20 rounded px-3 py-2">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={!stripe || processing}
        className="w-full rounded bg-forest py-3 text-sm font-sans font-medium text-mist hover:bg-meadow transition-colors duration-150 disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {processing ? 'Processing…' : `Pay £${order.total_amount}`}
      </button>
    </form>
  )
}

export default function CheckoutPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const [form, setForm] = useState<ShippingForm>(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [order, setOrder] = useState<Order | null>(null)
  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [selectedAddressId, setSelectedAddressId] = useState<string | null>(null)
  const [discountCode, setDiscountCode] = useState('')

  const { data: cart, isPending: cartLoading } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
  })

  const { data: savedAddresses = [] } = useQuery({
    queryKey: ['addresses'],
    queryFn: getAddresses,
    enabled: !!user,
  })

  const mutation = useMutation({
    mutationFn: async () => {
      const placed = await placeOrder({
        items: (cart?.items ?? []).map((i) => ({
          variant_id: i.variant,
          quantity: i.quantity,
        })),
        shipping_name: form.name,
        shipping_line1: form.line1,
        shipping_line2: form.line2,
        shipping_city: form.city,
        shipping_postcode: form.postcode,
        shipping_country: form.country,
        notes: form.notes,
        discount_code: discountCode.trim() || undefined,
      })
      const intent = await createPaymentIntent(placed.reference)
      return { order: placed, clientSecret: intent.client_secret }
    },
    onSuccess: ({ order: placed, clientSecret: secret }) => {
      setOrder(placed)
      setClientSecret(secret)
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Something went wrong. Please try again.'
      setError(msg)
    },
  })

  const handlePaymentSuccess = useCallback(async () => {
    await clearCart().catch(() => {})
    qc.invalidateQueries({ queryKey: ['cart'] })
    qc.invalidateQueries({ queryKey: ['orders'] })
    router.push(`/orders/${order!.reference}`)
  }, [order, qc, router])

  const set = (key: keyof ShippingForm) => (v: string) =>
    setForm((f) => ({ ...f, [key]: v }))

  const items = cart?.items ?? []
  const isEmpty = items.length === 0

  if (!cartLoading && !user) {
    router.replace('/login?next=/checkout')
    return null
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    mutation.mutate()
  }

  return (
    <>
      <Nav cartCount={cart?.item_count ?? 0} onCartClick={() => {}} />

      <main className="max-w-5xl mx-auto px-6 py-10">
        <Link
          href="/catalogue"
          className="inline-flex items-center gap-1.5 text-xs font-sans text-soil hover:text-forest transition-colors duration-150 mb-8"
        >
          <ChevronLeft className="w-3.5 h-3.5" strokeWidth={1.5} />
          Back to catalogue
        </Link>

        <h1 className="font-display italic text-2xl text-forest mb-8">Checkout</h1>

        {cartLoading ? (
          <p className="text-sm font-sans text-soil">Loading cart…</p>
        ) : isEmpty && !order ? (
          <div className="flex flex-col items-center py-24 text-center">
            <Package className="w-8 h-8 text-hoarfrost mb-4" strokeWidth={1} />
            <p className="font-display italic text-2xl text-hoarfrost mb-2">Your cart is empty.</p>
            <Link href="/catalogue" className="text-sm font-sans text-meadow underline-offset-2 hover:underline">
              Browse the catalogue
            </Link>
          </div>
        ) : (
          <div className="grid lg:grid-cols-[1fr_360px] gap-10 items-start">
            {clientSecret && order ? (
              <Elements
                stripe={stripePromise}
                options={{
                  clientSecret,
                  appearance: {
                    theme: 'flat',
                    variables: {
                      colorPrimary: '#2D4A3E',
                      colorBackground: '#ffffff',
                      colorText: '#1C2B27',
                      colorDanger: '#B85C38',
                      fontFamily: '"Inter", sans-serif',
                      borderRadius: '4px',
                    },
                  },
                }}
              >
                <PaymentStep
                  order={order}
                  onSuccess={handlePaymentSuccess}
                />
              </Elements>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                <h2 className="text-sm font-sans font-semibold text-forest">Shipping address</h2>

                {savedAddresses.length > 0 && (
                  <div className="space-y-2">
                    {savedAddresses.map((addr: Address) => (
                      <label
                        key={addr.id}
                        className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                          selectedAddressId === addr.id
                            ? 'border-forest bg-forest/5'
                            : 'border-hoarfrost hover:border-forest/40'
                        }`}
                      >
                        <input
                          type="radio"
                          name="saved_address"
                          value={addr.id}
                          checked={selectedAddressId === addr.id}
                          onChange={() => {
                            setSelectedAddressId(addr.id)
                            setForm({
                              name: addr.full_name,
                              line1: addr.line1,
                              line2: addr.line2,
                              city: addr.city,
                              postcode: addr.postcode,
                              country: addr.country,
                              notes: form.notes,
                            })
                          }}
                          className="mt-0.5 accent-forest"
                        />
                        <div>
                          <p className="text-sm font-sans font-medium text-forest">
                            {addr.full_name}
                            {addr.label && (
                              <span className="ml-2 text-[10px] font-sans bg-hoarfrost text-soil rounded px-1.5 py-0.5 align-middle">
                                {addr.label}
                              </span>
                            )}
                            {addr.is_default && (
                              <span className="ml-2 text-[10px] font-sans bg-meadow/15 text-[#245C38] rounded px-1.5 py-0.5 font-medium align-middle">
                                Default
                              </span>
                            )}
                          </p>
                          <p className="text-xs font-sans text-soil mt-0.5">
                            {addr.line1}{addr.line2 ? `, ${addr.line2}` : ''}, {addr.city}, {addr.postcode}
                          </p>
                        </div>
                      </label>
                    ))}
                    <label
                      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedAddressId === null
                          ? 'border-forest bg-forest/5'
                          : 'border-hoarfrost hover:border-forest/40'
                      }`}
                    >
                      <input
                        type="radio"
                        name="saved_address"
                        value=""
                        checked={selectedAddressId === null}
                        onChange={() => { setSelectedAddressId(null); setForm(EMPTY) }}
                        className="accent-forest"
                      />
                      <span className="text-sm font-sans text-soil">Enter a different address</span>
                    </label>
                  </div>
                )}

                {(savedAddresses.length === 0 || selectedAddressId === null) && (
                  <>
                    <Field label="Full name" name="name" value={form.name} onChange={set('name')} placeholder="Alex Johnson" />
                    <Field label="Address line 1" name="line1" value={form.line1} onChange={set('line1')} placeholder="12 Market Street" />
                    <Field label="Address line 2" name="line2" value={form.line2} onChange={set('line2')} required={false} placeholder="Flat 2 (optional)" />

                    <div className="grid sm:grid-cols-2 gap-5">
                      <Field label="City" name="city" value={form.city} onChange={set('city')} placeholder="London" />
                      <Field label="Postcode" name="postcode" value={form.postcode} onChange={set('postcode')} placeholder="SW1A 1AA" />
                    </div>

                    <div>
                      <label className="block text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium mb-1.5">
                        Country<span className="text-terracotta ml-0.5">*</span>
                      </label>
                      <select
                        value={form.country}
                        onChange={(e) => set('country')(e.target.value)}
                        required
                        className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150"
                      >
                        <option value="GB">United Kingdom</option>
                        <option value="IE">Ireland</option>
                        <option value="FR">France</option>
                        <option value="DE">Germany</option>
                        <option value="NL">Netherlands</option>
                      </select>
                    </div>
                  </>
                )}

                <div>
                  <label className="block text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium mb-1.5">
                    Order notes <span className="text-hoarfrost">(optional)</span>
                  </label>
                  <textarea
                    value={form.notes}
                    onChange={(e) => set('notes')(e.target.value)}
                    rows={3}
                    placeholder="Any special delivery instructions…"
                    className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150 resize-none"
                  />
                </div>

                <div>
                  <label className="block text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium mb-1.5">
                    Discount code <span className="text-hoarfrost">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={discountCode}
                    onChange={(e) => setDiscountCode(e.target.value.toUpperCase())}
                    placeholder="e.g. SAVE10"
                    autoCapitalize="characters"
                    className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans uppercase tracking-wide text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150"
                  />
                </div>

                {error && (
                  <p className="text-xs font-sans text-terracotta bg-terracotta/5 border border-terracotta/20 rounded px-3 py-2">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={mutation.isPending}
                  className="w-full rounded bg-forest py-3 text-sm font-sans font-medium text-mist hover:bg-meadow transition-colors duration-150 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {mutation.isPending ? 'Preparing order…' : 'Continue to payment'}
                </button>
                <p className="text-[11px] font-sans text-soil text-center">
                  Shipping, VAT and any discount are calculated on the next step.
                </p>
              </form>
            )}

            <OrderSummary items={items} total={cart?.total ?? '0.00'} />
          </div>
        )}
      </main>
    </>
  )
}
