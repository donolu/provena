'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MapPin, Star, Pencil, Trash2, Plus } from 'lucide-react'
import {
  getAddresses,
  createAddress,
  updateAddress,
  deleteAddress,
  setDefaultAddress,
} from '@/lib/api/addresses'
import type { Address, AddressPayload } from '@/lib/api/addresses'

const COUNTRIES = [
  { code: 'GB', name: 'United Kingdom' },
  { code: 'IE', name: 'Ireland' },
  { code: 'FR', name: 'France' },
  { code: 'DE', name: 'Germany' },
  { code: 'NL', name: 'Netherlands' },
]

const EMPTY_FORM: AddressPayload = {
  label: '',
  full_name: '',
  line1: '',
  line2: '',
  city: '',
  postcode: '',
  country: 'GB',
}

function Field({
  label,
  value,
  onChange,
  required = true,
  placeholder = '',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  required?: boolean
  placeholder?: string
}) {
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium mb-1.5">
        {label}
        {required && <span className="text-terracotta ml-0.5">*</span>}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full border border-hoarfrost rounded px-3 py-2 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors"
      />
    </div>
  )
}

function AddressForm({
  initial,
  onSubmit,
  onCancel,
  pending,
}: {
  initial: AddressPayload
  onSubmit: (data: AddressPayload) => void
  onCancel: () => void
  pending: boolean
}) {
  const [form, setForm] = useState<AddressPayload>(initial)
  const set = (key: keyof AddressPayload) => (v: string) => setForm((f) => ({ ...f, [key]: v }))

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSubmit(form) }}
      className="space-y-4 p-5 bg-white border border-hoarfrost rounded-lg"
    >
      <Field label="Label (optional)" value={form.label} onChange={set('label')} required={false} placeholder="e.g. Home, Work" />
      <Field label="Full name" value={form.full_name} onChange={set('full_name')} placeholder="Alex Johnson" />
      <Field label="Address line 1" value={form.line1} onChange={set('line1')} placeholder="12 Market Street" />
      <Field label="Address line 2" value={form.line2} onChange={set('line2')} required={false} placeholder="Flat 2 (optional)" />

      <div className="grid sm:grid-cols-2 gap-4">
        <Field label="City" value={form.city} onChange={set('city')} placeholder="London" />
        <Field label="Postcode" value={form.postcode} onChange={set('postcode')} placeholder="SW1A 1AA" />
      </div>

      <div>
        <label className="block text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium mb-1.5">
          Country<span className="text-terracotta ml-0.5">*</span>
        </label>
        <select
          value={form.country}
          onChange={(e) => set('country')(e.target.value)}
          required
          className="w-full border border-hoarfrost rounded px-3 py-2 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors"
        >
          {COUNTRIES.map((c) => (
            <option key={c.code} value={c.code}>{c.name}</option>
          ))}
        </select>
      </div>

      <div className="flex gap-3 pt-1">
        <button
          type="submit"
          disabled={pending}
          className="rounded bg-forest px-4 py-2 text-sm font-sans font-medium text-mist hover:bg-meadow transition-colors disabled:opacity-60"
        >
          {pending ? 'Saving…' : 'Save address'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded border border-hoarfrost px-4 py-2 text-sm font-sans text-soil hover:text-forest hover:border-forest transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

function AddressCard({
  address,
  onEdit,
  onDelete,
  onSetDefault,
}: {
  address: Address
  onEdit: () => void
  onDelete: () => void
  onSetDefault: () => void
}) {
  const countryName = COUNTRIES.find((c) => c.code === address.country)?.name ?? address.country

  return (
    <div className={`p-4 rounded-lg border transition-colors ${address.is_default ? 'border-forest bg-forest/5' : 'border-hoarfrost bg-white'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <MapPin size={14} strokeWidth={1.5} className={`mt-0.5 shrink-0 ${address.is_default ? 'text-forest' : 'text-soil'}`} />
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-sans font-medium text-forest">{address.full_name}</p>
              {address.label && (
                <span className="text-[10px] font-sans bg-hoarfrost text-soil rounded px-1.5 py-0.5">
                  {address.label}
                </span>
              )}
              {address.is_default && (
                <span className="text-[10px] font-sans bg-meadow/15 text-[#245C38] rounded px-1.5 py-0.5 font-medium">
                  Default
                </span>
              )}
            </div>
            <p className="text-xs font-sans text-soil mt-1 leading-relaxed">
              {address.line1}
              {address.line2 && `, ${address.line2}`}
              <br />
              {address.city}, {address.postcode}
              <br />
              {countryName}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {!address.is_default && (
            <button
              onClick={onSetDefault}
              title="Set as default"
              className="p-1.5 text-soil hover:text-marigold transition-colors"
            >
              <Star size={14} strokeWidth={1.5} />
            </button>
          )}
          <button onClick={onEdit} title="Edit" className="p-1.5 text-soil hover:text-forest transition-colors">
            <Pencil size={14} strokeWidth={1.5} />
          </button>
          <button onClick={onDelete} title="Delete" className="p-1.5 text-soil hover:text-terracotta transition-colors">
            <Trash2 size={14} strokeWidth={1.5} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function AddressesPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Address | null>(null)

  const { data: addresses = [], isPending } = useQuery({
    queryKey: ['addresses'],
    queryFn: getAddresses,
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: ['addresses'] })

  const createMutation = useMutation({
    mutationFn: createAddress,
    onSuccess: () => { invalidate(); setShowForm(false) },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AddressPayload> }) =>
      updateAddress(id, data),
    onSuccess: () => { invalidate(); setEditing(null) },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAddress,
    onSuccess: invalidate,
  })

  const defaultMutation = useMutation({
    mutationFn: setDefaultAddress,
    onSuccess: invalidate,
  })

  return (
    <div className="max-w-xl mx-auto px-6 py-8">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-display italic text-2xl text-forest">Saved addresses</h1>
          <p className="text-sm text-soil font-sans mt-0.5">
            {addresses.length} address{addresses.length !== 1 ? 'es' : ''} saved
          </p>
        </div>
        {!showForm && !editing && (
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-1.5 rounded bg-forest px-3 py-2 text-xs font-sans font-medium text-mist hover:bg-meadow transition-colors"
          >
            <Plus size={13} strokeWidth={2} />
            Add address
          </button>
        )}
      </div>

      {showForm && (
        <div className="mb-4">
          <AddressForm
            initial={EMPTY_FORM}
            onSubmit={(data) => createMutation.mutate(data)}
            onCancel={() => setShowForm(false)}
            pending={createMutation.isPending}
          />
        </div>
      )}

      {isPending ? (
        <p className="text-sm font-sans text-soil">Loading…</p>
      ) : addresses.length === 0 && !showForm ? (
        <div className="flex flex-col items-center py-16 text-center border border-dashed border-hoarfrost rounded-lg">
          <MapPin size={28} strokeWidth={1} className="text-hoarfrost mb-3" />
          <p className="font-display italic text-lg text-hoarfrost mb-1">No saved addresses yet.</p>
          <button
            onClick={() => setShowForm(true)}
            className="text-sm font-sans text-meadow hover:underline underline-offset-2 mt-1"
          >
            Add your first address
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {addresses.map((addr) =>
            editing?.id === addr.id ? (
              <AddressForm
                key={addr.id}
                initial={{
                  label: addr.label,
                  full_name: addr.full_name,
                  line1: addr.line1,
                  line2: addr.line2,
                  city: addr.city,
                  postcode: addr.postcode,
                  country: addr.country,
                }}
                onSubmit={(data) => updateMutation.mutate({ id: addr.id, data })}
                onCancel={() => setEditing(null)}
                pending={updateMutation.isPending}
              />
            ) : (
              <AddressCard
                key={addr.id}
                address={addr}
                onEdit={() => { setShowForm(false); setEditing(addr) }}
                onDelete={() => deleteMutation.mutate(addr.id)}
                onSetDefault={() => defaultMutation.mutate(addr.id)}
              />
            )
          )}
        </div>
      )}
    </div>
  )
}
