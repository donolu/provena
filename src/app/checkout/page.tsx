'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, Package } from 'lucide-react'
import Link from 'next/link'
import { Nav } from '@/components/nav'
import { getCart, clearCart } from '@/lib/api/cart'
import { placeOrder } from '@/lib/api/orders'
import { useAuthStore } from '@/store/auth'

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

export default function CheckoutPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const [form, setForm] = useState<ShippingForm>(EMPTY)
  const [error, setError] = useState<string | null>(null)

  const { data: cart, isPending: cartLoading } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
    enabled: !!user,
  })

  const mutation = useMutation({
    mutationFn: () =>
      placeOrder({
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
      }),
    onSuccess: async (order) => {
      await clearCart().catch(() => {})
      qc.invalidateQueries({ queryKey: ['cart'] })
      qc.invalidateQueries({ queryKey: ['orders'] })
      router.push(`/orders/${order.reference}`)
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Something went wrong. Please try again.'
      setError(msg)
    },
  })

  const set = (key: keyof ShippingForm) => (v: string) =>
    setForm((f) => ({ ...f, [key]: v }))

  const items = cart?.items ?? []
  const isEmpty = items.length === 0

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
        ) : isEmpty ? (
          <div className="flex flex-col items-center py-24 text-center">
            <Package className="w-8 h-8 text-hoarfrost mb-4" strokeWidth={1} />
            <p className="font-display italic text-2xl text-hoarfrost mb-2">Your cart is empty.</p>
            <Link href="/catalogue" className="text-sm font-sans text-meadow underline-offset-2 hover:underline">
              Browse the catalogue
            </Link>
          </div>
        ) : (
          <div className="grid lg:grid-cols-[1fr_360px] gap-10 items-start">
            {/* Shipping form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              <h2 className="text-sm font-sans font-semibold text-forest">Shipping address</h2>

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
                {mutation.isPending ? 'Placing order…' : `Place order · £${cart?.total}`}
              </button>
            </form>

            {/* Order summary */}
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
                <span className="text-sm font-sans text-soil">Total</span>
                <span className="font-mono text-base font-semibold text-forest">£{cart?.total}</span>
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  )
}
