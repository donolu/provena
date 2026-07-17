'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Truck } from 'lucide-react'
import { getMySupplierProfile, updateMySupplierProfile } from '@/lib/api/suppliers'
import type { ShippingPolicy, SupplierProfile } from '@/lib/api/types'

interface FormState {
  shipping_policy: ShippingPolicy
  shipping_flat_rate: string
  shipping_per_item_rate: string
  free_shipping_threshold: string
  vat_number: string
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="block text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium mb-1.5">
      {children}
    </label>
  )
}

const inputClass =
  'w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150'

export default function SupplierSettingsPage() {
  const { data: profile, isPending } = useQuery({
    queryKey: ['supplier', 'profile'],
    queryFn: getMySupplierProfile,
  })

  if (isPending || !profile) {
    return <div className="px-6 py-8 max-w-2xl mx-auto text-sm font-sans text-soil">Loading…</div>
  }

  return <SettingsForm profile={profile} />
}

function SettingsForm({ profile }: { profile: SupplierProfile }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<FormState>(() => ({
    shipping_policy: profile.shipping_policy,
    shipping_flat_rate: profile.shipping_flat_rate,
    shipping_per_item_rate: profile.shipping_per_item_rate,
    free_shipping_threshold: profile.free_shipping_threshold ?? '',
    vat_number: profile.vat_number,
  }))
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (f: FormState) =>
      updateMySupplierProfile({
        shipping_policy: f.shipping_policy,
        shipping_flat_rate: f.shipping_flat_rate || '0.00',
        shipping_per_item_rate: f.shipping_per_item_rate || '0.00',
        free_shipping_threshold: f.free_shipping_threshold.trim() === '' ? null : f.free_shipping_threshold,
        vat_number: f.vat_number.trim(),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['supplier', 'profile'] }),
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Could not save. Please check the values and try again.'
      setError(msg)
    },
  })

  const set = (key: keyof FormState) => (v: string) =>
    setForm((f) => ({ ...f, [key]: v }))

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    mutation.mutate(form)
  }

  const policy = form.shipping_policy
  const platformDelivered = profile.fulfilment_mode === 'PLATFORM_DELIVERY'

  return (
    <div className="px-6 py-8 max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display italic text-2xl text-forest">Settings</h1>
        <p className="text-sm text-soil font-sans mt-0.5">Delivery charges and VAT details</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="bg-white rounded-lg border border-hoarfrost p-6 space-y-5">
          <h2 className="text-sm font-sans font-semibold text-forest">Shipping</h2>

          {platformDelivered ? (
            <div className="flex items-start gap-2.5 px-4 py-3 bg-meadow/10 border border-meadow/30 rounded-lg">
              <Truck className="w-4 h-4 text-meadow shrink-0 mt-0.5" strokeWidth={1.5} />
              <div>
                <p className="text-sm font-sans text-forest font-medium">
                  Delivery handled by Provena
                </p>
                <p className="text-xs font-sans text-soil mt-0.5">
                  Provena arranges the courier and sets the delivery fee for your orders — you don&apos;t
                  need to configure shipping. You fulfil the goods; we handle delivery.
                </p>
              </div>
            </div>
          ) : (
            <>
              <div>
                <FieldLabel>Delivery charge</FieldLabel>
                <select
                  value={policy}
                  onChange={(e) => set('shipping_policy')(e.target.value)}
                  className={inputClass}
                >
                  <option value="FLAT">Flat rate per order</option>
                  <option value="FREE_OVER_THRESHOLD">Flat rate, free over a threshold</option>
                  <option value="PER_ITEM">Per item</option>
                </select>
              </div>

              {(policy === 'FLAT' || policy === 'FREE_OVER_THRESHOLD') && (
                <div>
                  <FieldLabel>Flat rate (£)</FieldLabel>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.shipping_flat_rate}
                    onChange={(e) => set('shipping_flat_rate')(e.target.value)}
                    className={inputClass}
                  />
                  <p className="text-[11px] font-sans text-soil mt-1">Set to 0 for free delivery.</p>
                </div>
              )}

              {policy === 'FREE_OVER_THRESHOLD' && (
                <div>
                  <FieldLabel>Free over (£)</FieldLabel>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.free_shipping_threshold}
                    onChange={(e) => set('free_shipping_threshold')(e.target.value)}
                    placeholder="e.g. 40.00"
                    className={inputClass}
                  />
                  <p className="text-[11px] font-sans text-soil mt-1">
                    Orders of goods at or above this value ship free.
                  </p>
                </div>
              )}

              {policy === 'PER_ITEM' && (
                <div>
                  <FieldLabel>Rate per item (£)</FieldLabel>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.shipping_per_item_rate}
                    onChange={(e) => set('shipping_per_item_rate')(e.target.value)}
                    className={inputClass}
                  />
                </div>
              )}
            </>
          )}
        </section>

        <section className="bg-white rounded-lg border border-hoarfrost p-6 space-y-5">
          <h2 className="text-sm font-sans font-semibold text-forest">VAT</h2>
          <div>
            <FieldLabel>VAT number</FieldLabel>
            <input
              type="text"
              value={form.vat_number}
              onChange={(e) => set('vat_number')(e.target.value)}
              placeholder="e.g. GB123456789"
              className={inputClass}
            />
            <p className="text-[11px] font-sans text-soil mt-1">
              Shown on buyer receipts for orders you fulfil.
            </p>
          </div>
        </section>

        {error && (
          <p className="text-xs font-sans text-terracotta bg-terracotta/5 border border-terracotta/20 rounded px-3 py-2">
            {error}
          </p>
        )}

        {mutation.isSuccess && !mutation.isPending && (
          <div className="flex items-center gap-2 text-sm font-sans text-meadow">
            <CheckCircle className="w-4 h-4" strokeWidth={1.5} />
            Saved.
          </div>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded bg-forest px-6 py-2.5 text-sm font-sans font-medium text-mist hover:bg-meadow transition-colors duration-150 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? 'Saving…' : 'Save changes'}
        </button>
      </form>
    </div>
  )
}
