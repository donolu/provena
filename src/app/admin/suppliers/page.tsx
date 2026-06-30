'use client'

import { useState } from 'react'
import { Star, CheckCircle, XCircle } from 'lucide-react'
import { StatusBadge } from '@/components/supplier/status-badge'
import { ADMIN_SUPPLIERS, type AdminSupplier, type SupplierStatus } from '@/lib/admin-data'

type Tab = 'ALL' | SupplierStatus

const TABS: { key: Tab; label: string }[] = [
  { key: 'ALL',       label: 'All' },
  { key: 'APPROVED',  label: 'Approved' },
  { key: 'PENDING',   label: 'Pending' },
  { key: 'REJECTED',  label: 'Rejected' },
  { key: 'SUSPENDED', label: 'Suspended' },
]

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<AdminSupplier[]>(ADMIN_SUPPLIERS)
  const [filter, setFilter]       = useState<Tab>('ALL')
  const [confirming, setConfirming] = useState<{ id: string; action: 'approve' | 'reject' } | null>(null)

  const displayed = filter === 'ALL' ? suppliers : suppliers.filter((s) => s.status === filter)

  function approve(id: string) {
    setSuppliers((prev) => prev.map((s) => s.id === id ? { ...s, status: 'APPROVED' as SupplierStatus } : s))
    setConfirming(null)
  }

  function reject(id: string) {
    setSuppliers((prev) => prev.map((s) => s.id === id ? { ...s, status: 'REJECTED' as SupplierStatus } : s))
    setConfirming(null)
  }

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display italic text-2xl text-forest">Suppliers</h1>
        <p className="text-sm text-soil font-sans mt-0.5">{suppliers.length} registered suppliers</p>
      </div>

      {/* Status tabs */}
      <div className="border-b border-hoarfrost mb-6 -mx-6 px-6 overflow-x-auto">
        <div className="flex no-scrollbar">
          {TABS.map(({ key, label }) => {
            const count = key === 'ALL' ? suppliers.length : suppliers.filter((s) => s.status === key).length
            const active = filter === key
            return (
              <button
                key={key}
                onClick={() => setFilter(key)}
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
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-hoarfrost">
                {['Supplier', 'Location', 'Email', 'Products', 'Rating', 'Joined', 'Status', ''].map((h, i) => (
                  <th key={i} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hoarfrost">
              {displayed.map((s) => (
                <>
                  <tr key={s.id} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3.5">
                      <p className="text-sm font-sans font-medium text-forest">{s.business_name}</p>
                    </td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{s.location}</td>
                    <td className="px-4 py-3.5 text-xs font-mono text-soil">{s.email}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-forest text-center">{s.product_count}</td>
                    <td className="px-4 py-3.5">
                      {s.rating != null ? (
                        <div className="flex items-center gap-1">
                          <Star className="w-3 h-3 fill-marigold text-marigold" strokeWidth={0} />
                          <span className="font-mono text-xs text-forest">{s.rating.toFixed(1)}</span>
                        </div>
                      ) : (
                        <span className="text-xs text-hoarfrost">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(s.joined_at)}</td>
                    <td className="px-4 py-3.5"><StatusBadge status={s.status} /></td>
                    <td className="px-4 py-3.5">
                      {s.status === 'PENDING' && confirming?.id !== s.id && (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setConfirming({ id: s.id, action: 'approve' })}
                            className="flex items-center gap-1 text-xs font-sans text-meadow hover:underline underline-offset-2 transition-colors"
                          >
                            <CheckCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
                            Approve
                          </button>
                          <span className="text-hoarfrost">·</span>
                          <button
                            onClick={() => setConfirming({ id: s.id, action: 'reject' })}
                            className="flex items-center gap-1 text-xs font-sans text-soil hover:text-forest hover:underline underline-offset-2 transition-colors"
                          >
                            <XCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
                            Reject
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>

                  {/* Inline confirmation row */}
                  {confirming?.id === s.id && (
                    <tr key={`${s.id}-confirm`} className="bg-mist border-b border-hoarfrost">
                      <td colSpan={8} className="px-6 py-3">
                        <div className="flex items-center gap-4">
                          <p className="text-sm font-sans text-forest">
                            {confirming.action === 'approve'
                              ? <>Approve <span className="font-medium">{s.business_name}</span>?</>
                              : <>Reject <span className="font-medium">{s.business_name}</span>?</>
                            }
                          </p>
                          <button
                            onClick={() => confirming.action === 'approve' ? approve(s.id) : reject(s.id)}
                            className={`text-xs font-sans font-medium px-3 py-1.5 rounded transition-colors ${
                              confirming.action === 'approve'
                                ? 'bg-meadow text-white hover:bg-forest'
                                : 'bg-soil text-white hover:bg-forest'
                            }`}
                          >
                            Confirm {confirming.action}
                          </button>
                          <button
                            onClick={() => setConfirming(null)}
                            className="text-xs font-sans text-soil hover:text-forest underline-offset-2 hover:underline"
                          >
                            Cancel
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
