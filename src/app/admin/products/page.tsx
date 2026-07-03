'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Star } from 'lucide-react'
import { getAdminProducts, adminToggleFeature } from '@/lib/api/admin'
import type { Product } from '@/lib/api/types'

const STATUS_BADGE: Record<string, string> = {
  ACTIVE:   'bg-meadow/15 text-[#245C38]',
  DRAFT:    'bg-hoarfrost text-soil',
  ARCHIVED: 'bg-red-50 text-red-600',
}

type StatusFilter = 'ALL' | 'ACTIVE' | 'DRAFT' | 'ARCHIVED'

const TABS: { key: StatusFilter; label: string }[] = [
  { key: 'ALL',      label: 'All' },
  { key: 'ACTIVE',   label: 'Active' },
  { key: 'DRAFT',    label: 'Drafts' },
  { key: 'ARCHIVED', label: 'Archived' },
]

export default function AdminProductsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [search, setSearch] = useState('')
  const qc = useQueryClient()

  const { data: products = [], isPending } = useQuery({
    queryKey: ['admin', 'products', statusFilter],
    queryFn: () => getAdminProducts(statusFilter === 'ALL' ? undefined : { status: statusFilter }),
  })

  const toggleFeature = useMutation({
    mutationFn: (slug: string) => adminToggleFeature(slug),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'products'] }),
  })

  const filtered = search
    ? products.filter(
        (p) =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.supplier_name.toLowerCase().includes(search.toLowerCase()),
      )
    : products

  const featuredCount = products.filter((p) => p.is_featured).length

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-display italic text-2xl text-forest">Products</h1>
          <p className="text-sm text-soil font-sans mt-0.5">
            {products.length} product{products.length !== 1 ? 's' : ''}
            {featuredCount > 0 && (
              <> · <span className="text-marigold font-medium">{featuredCount} featured</span></>
            )}
          </p>
        </div>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search products…"
          className="text-sm font-sans text-forest placeholder-soil/60 bg-white border border-hoarfrost rounded px-3 py-2 w-52 focus:outline-none focus:border-forest transition-colors"
        />
      </div>

      <div className="border-b border-hoarfrost mb-6 -mx-6 px-6">
        <div className="flex">
          {TABS.map(({ key, label }) => {
            const count = key === 'ALL' ? products.length : products.filter((p) => p.status === key).length
            const active = statusFilter === key
            return (
              <button
                key={key}
                onClick={() => setStatusFilter(key)}
                className={[
                  'relative flex-shrink-0 px-4 py-3 text-xs font-sans whitespace-nowrap transition-colors duration-150',
                  active ? 'text-forest font-medium' : 'text-soil hover:text-forest',
                ].join(' ')}
              >
                {label}
                {count > 0 && (
                  <span className={`ml-1.5 font-mono text-[10px] ${active ? 'text-soil' : 'text-hoarfrost'}`}>{count}</span>
                )}
                {active && <span className="absolute bottom-0 left-4 right-4 h-0.5 bg-forest rounded-full" />}
              </button>
            )
          })}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
        {isPending ? (
          <div className="px-4 py-12 text-center text-sm font-sans text-soil">Loading products…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  {['Product', 'Supplier', 'Category', 'Price', 'Status', 'Featured'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {filtered.map((p: Product) => (
                  <tr key={p.id} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3.5">
                      <p className="text-sm font-sans font-medium text-forest">{p.name}</p>
                      {p.variants[0] && (
                        <p className="text-[10px] font-mono text-soil mt-0.5">{p.variants[0].sku}</p>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil">{p.supplier_name}</td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil">{p.category_name ?? '-'}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-forest">
                      {p.variants[0] ? `£${p.variants[0].price}` : '-'}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-sans font-semibold uppercase tracking-wide ${STATUS_BADGE[p.status] ?? ''}`}>
                        {p.status.toLowerCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <button
                        onClick={() => toggleFeature.mutate(p.slug)}
                        disabled={toggleFeature.isPending}
                        title={p.is_featured ? 'Remove from homepage' : 'Feature on homepage'}
                        className="transition-colors disabled:opacity-40"
                      >
                        <Star
                          size={16}
                          strokeWidth={1.5}
                          className={p.is_featured ? 'fill-marigold text-marigold' : 'text-hoarfrost hover:text-marigold'}
                        />
                      </button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-sm font-sans text-soil">
                      {search ? 'No products match your search.' : 'No products yet.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
