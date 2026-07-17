'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { Pagination } from '@/components/pagination'
import { getAdminDiscounts, createDiscount, updateDiscount } from '@/lib/api/admin'
import type { DiscountCode, DiscountFunding, DiscountType } from '@/lib/api/types'

const inputClass =
  'w-full border border-hoarfrost rounded px-3 py-2 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors'

interface CreateState {
  code: string
  discount_type: DiscountType
  value: string
  funded_by: DiscountFunding
  minimum_spend: string
  max_uses: string
  max_uses_per_buyer: string
}

const EMPTY: CreateState = {
  code: '',
  discount_type: 'PERCENTAGE',
  value: '',
  funded_by: 'PLATFORM',
  minimum_spend: '0',
  max_uses: '',
  max_uses_per_buyer: '',
}

function CreateForm({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<CreateState>(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof CreateState) => (v: string) => setForm((f) => ({ ...f, [k]: v }))

  const mutation = useMutation({
    mutationFn: () =>
      createDiscount({
        code: form.code.trim().toUpperCase(),
        discount_type: form.discount_type,
        value: form.value,
        funded_by: form.funded_by,
        minimum_spend: form.minimum_spend || '0',
        max_uses: form.max_uses ? Number(form.max_uses) : null,
        max_uses_per_buyer: form.max_uses_per_buyer ? Number(form.max_uses_per_buyer) : null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'discounts'] })
      setForm(EMPTY)
      onDone()
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data
      setError(data ? JSON.stringify(data) : 'Could not create the code.')
    },
  })

  return (
    <div className="bg-white rounded-lg border border-hoarfrost p-5 mb-6 space-y-4">
      <h2 className="text-sm font-sans font-semibold text-forest">New discount code</h2>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <input
          placeholder="CODE"
          value={form.code}
          onChange={(e) => set('code')(e.target.value.toUpperCase())}
          className={`${inputClass} uppercase`}
        />
        <select value={form.discount_type} onChange={(e) => set('discount_type')(e.target.value)} className={inputClass}>
          <option value="PERCENTAGE">Percentage</option>
          <option value="FIXED">Fixed amount</option>
        </select>
        <input
          type="number"
          step="0.01"
          min="0"
          placeholder={form.discount_type === 'PERCENTAGE' ? '% e.g. 10' : '£ e.g. 5.00'}
          value={form.value}
          onChange={(e) => set('value')(e.target.value)}
          className={inputClass}
        />
        <select value={form.funded_by} onChange={(e) => set('funded_by')(e.target.value)} className={inputClass}>
          <option value="PLATFORM">Funded by platform</option>
          <option value="SUPPLIER">Funded by supplier</option>
        </select>
        <input
          type="number"
          step="0.01"
          min="0"
          placeholder="Min spend £"
          value={form.minimum_spend}
          onChange={(e) => set('minimum_spend')(e.target.value)}
          className={inputClass}
        />
        <input
          type="number"
          min="1"
          placeholder="Max uses (blank = ∞)"
          value={form.max_uses}
          onChange={(e) => set('max_uses')(e.target.value)}
          className={inputClass}
        />
        <input
          type="number"
          min="1"
          placeholder="Per buyer (blank = ∞)"
          value={form.max_uses_per_buyer}
          onChange={(e) => set('max_uses_per_buyer')(e.target.value)}
          className={inputClass}
        />
        <button
          type="button"
          onClick={() => {
            setError(null)
            if (form.code.trim() && form.value) mutation.mutate()
          }}
          disabled={mutation.isPending}
          className="flex items-center justify-center gap-1.5 rounded bg-forest px-4 py-2 text-sm font-sans font-medium text-mist hover:bg-meadow transition-colors disabled:opacity-60"
        >
          <Plus className="w-3.5 h-3.5" strokeWidth={2} />
          {mutation.isPending ? 'Creating…' : 'Create'}
        </button>
      </div>
      {error && <p className="text-xs font-sans text-terracotta">{error}</p>}
    </div>
  )
}

function Row({ code }: { code: DiscountCode }) {
  const qc = useQueryClient()
  const mutation = useMutation({
    mutationFn: (is_active: boolean) => updateDiscount(code.id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'discounts'] }),
  })
  const value = code.discount_type === 'PERCENTAGE' ? `${code.value}%` : `£${code.value}`
  const uses = code.max_uses ? `${code.times_used}/${code.max_uses}` : `${code.times_used}`
  return (
    <tr className="border-t border-hoarfrost">
      <td className="py-2.5 px-3 font-mono text-xs text-forest">{code.code}</td>
      <td className="py-2.5 px-3 text-sm text-forest">{value}</td>
      <td className="py-2.5 px-3 text-xs text-soil">{code.funded_by === 'PLATFORM' ? 'Platform' : 'Supplier'}</td>
      <td className="py-2.5 px-3 font-mono text-xs text-soil">£{code.minimum_spend}</td>
      <td className="py-2.5 px-3 font-mono text-xs text-soil">{uses}</td>
      <td className="py-2.5 px-3">
        <span
          className={`text-[11px] font-sans rounded px-2 py-0.5 ${
            code.is_active ? 'bg-meadow/15 text-[#245C38]' : 'bg-hoarfrost text-soil'
          }`}
        >
          {code.is_active ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td className="py-2.5 px-3 text-right">
        <button
          type="button"
          onClick={() => mutation.mutate(!code.is_active)}
          disabled={mutation.isPending}
          className="text-xs font-sans text-forest hover:text-meadow underline-offset-2 hover:underline disabled:opacity-50"
        >
          {code.is_active ? 'Deactivate' : 'Reactivate'}
        </button>
      </td>
    </tr>
  )
}

export default function AdminDiscountsPage() {
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isPending } = useQuery({
    queryKey: ['admin', 'discounts', page],
    queryFn: () => getAdminDiscounts(page),
  })
  const codes = data?.results ?? []

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display italic text-2xl text-forest">Discounts</h1>
          <p className="text-sm text-soil font-sans mt-0.5">Create and manage voucher codes</p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate((s) => !s)}
          className="flex items-center gap-1.5 rounded bg-forest px-4 py-2 text-sm font-sans font-medium text-mist hover:bg-meadow transition-colors"
        >
          <Plus className="w-3.5 h-3.5" strokeWidth={2} />
          New code
        </button>
      </div>

      {showCreate && <CreateForm onDone={() => setShowCreate(false)} />}

      {isPending ? (
        <p className="text-sm font-sans text-soil">Loading…</p>
      ) : codes.length === 0 ? (
        <p className="text-sm font-sans text-soil">No discount codes yet.</p>
      ) : (
        <div className="bg-white rounded-lg border border-hoarfrost overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-[0.12em] text-soil font-sans">
                <th className="py-2.5 px-3 font-medium">Code</th>
                <th className="py-2.5 px-3 font-medium">Value</th>
                <th className="py-2.5 px-3 font-medium">Funded by</th>
                <th className="py-2.5 px-3 font-medium">Min spend</th>
                <th className="py-2.5 px-3 font-medium">Uses</th>
                <th className="py-2.5 px-3 font-medium">Status</th>
                <th className="py-2.5 px-3" />
              </tr>
            </thead>
            <tbody>
              {codes.map((c) => (
                <Row key={c.id} code={c} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination page={page} count={data?.count ?? 0} onChange={setPage} />
    </div>
  )
}
