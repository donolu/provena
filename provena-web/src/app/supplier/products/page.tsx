'use client'

import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, MoreHorizontal, Upload, Download, ChevronDown, ChevronRight, AlertCircle, CheckCircle2, X } from 'lucide-react'
import { StatusBadge } from '@/components/supplier/status-badge'
import { Pagination } from '@/components/pagination'
import { getMyProducts } from '@/lib/api/catalogue'
import { previewUpload, confirmUpload, getUploadTemplate } from '@/lib/api/bulk-upload'
import type { Product } from '@/lib/api/types'
import type { UploadProductPreview, UploadError, PreviewResult } from '@/lib/api/bulk-upload'

// ---------------------------------------------------------------------------
// Upload modal
// ---------------------------------------------------------------------------

type UploadStep = 'pick' | 'preview' | 'errors' | 'success'

function UploadModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [step, setStep] = useState<UploadStep>('pick')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<PreviewResult | null>(null)
  const [createdCount, setCreatedCount] = useState(0)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const fileRef = useRef<HTMLInputElement>(null)

  const previewMutation = useMutation({
    mutationFn: (f: File) => previewUpload(f),
    onSuccess: (result) => {
      setPreview(result)
      setStep(result.valid ? 'preview' : 'errors')
    },
  })

  const confirmMutation = useMutation({
    mutationFn: (f: File) => confirmUpload(f),
    onSuccess: (result) => {
      setCreatedCount(result.created)
      setStep('success')
    },
  })

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    previewMutation.mutate(f)
  }

  function toggleExpand(name: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const errors: UploadError[] = preview?.errors ?? []
  const products: UploadProductPreview[] = preview?.products ?? []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-hoarfrost">
          <h2 className="font-display italic text-lg text-forest">
            {step === 'pick' && 'Upload products'}
            {step === 'preview' && 'Review import'}
            {step === 'errors' && 'Fix errors before importing'}
            {step === 'success' && 'Import complete'}
          </h2>
          <button onClick={onClose} className="text-soil hover:text-forest transition-colors">
            <X size={18} strokeWidth={1.5} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

          {/* Step: pick */}
          {step === 'pick' && (
            <>
              <p className="text-sm font-sans text-soil">
                Upload a CSV, XLSX, or XLS file to create multiple products at once. All imported
                products will be saved as drafts for you to review and publish individually.
              </p>
              <div
                className="border-2 border-dashed border-hoarfrost rounded-lg p-8 text-center cursor-pointer hover:border-forest/50 transition-colors"
                onClick={() => fileRef.current?.click()}
              >
                <Upload size={24} strokeWidth={1.5} className="mx-auto text-hoarfrost mb-2" />
                <p className="text-sm font-sans font-medium text-forest">
                  {previewMutation.isPending ? 'Parsing file…' : 'Click to choose a file'}
                </p>
                <p className="text-xs font-sans text-soil mt-1">CSV, XLSX or XLS · max 500 rows · 5 MB</p>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
              {previewMutation.isError && (
                <p className="text-xs font-sans text-terracotta">
                  {(previewMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Could not parse the file.'}
                </p>
              )}
            </>
          )}

          {/* Step: preview */}
          {step === 'preview' && (
            <>
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} strokeWidth={1.5} className="text-meadow shrink-0" />
                <p className="text-sm font-sans text-forest">
                  <strong>{preview?.product_count}</strong> product{preview?.product_count !== 1 ? 's' : ''} ·{' '}
                  <strong>{preview?.row_count}</strong> variant{preview?.row_count !== 1 ? 's' : ''} will be created as drafts.
                </p>
              </div>
              <div className="space-y-2">
                {products.map((p) => (
                  <div key={p.name} className="border border-hoarfrost rounded-lg overflow-hidden">
                    <button
                      className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-mist/40 transition-colors"
                      onClick={() => toggleExpand(p.name)}
                    >
                      <div>
                        <span className="text-sm font-sans font-medium text-forest">{p.name}</span>
                        {p.category && (
                          <span className="ml-2 text-[10px] bg-hoarfrost text-soil rounded px-1.5 py-0.5 font-sans">
                            {p.category}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-sans text-soil">{p.variants.length} variant{p.variants.length !== 1 ? 's' : ''}</span>
                        {expanded.has(p.name) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </div>
                    </button>
                    {expanded.has(p.name) && (
                      <div className="border-t border-hoarfrost divide-y divide-hoarfrost">
                        {p.variants.map((v) => (
                          <div key={v.sku} className="px-4 py-2.5 flex items-center justify-between">
                            <div>
                              <span className="text-xs font-sans font-medium text-forest">{v.name}</span>
                              <span className="ml-2 font-mono text-[10px] text-soil">{v.sku}</span>
                            </div>
                            <span className="font-mono text-xs text-forest">£{v.price}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Step: errors */}
          {step === 'errors' && (
            <>
              <div className="flex items-center gap-2">
                <AlertCircle size={16} strokeWidth={1.5} className="text-terracotta shrink-0" />
                <p className="text-sm font-sans text-forest">
                  <strong>{errors.length}</strong> error{errors.length !== 1 ? 's' : ''} found. Fix your file and re-upload.
                </p>
              </div>
              <div className="border border-hoarfrost rounded-lg overflow-hidden">
                <table className="w-full text-xs font-sans">
                  <thead>
                    <tr className="border-b border-hoarfrost bg-mist/40">
                      <th className="text-left px-3 py-2 text-[10px] uppercase tracking-[0.12em] text-soil font-medium w-12">Row</th>
                      <th className="text-left px-3 py-2 text-[10px] uppercase tracking-[0.12em] text-soil font-medium w-36">Column</th>
                      <th className="text-left px-3 py-2 text-[10px] uppercase tracking-[0.12em] text-soil font-medium">Issue</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-hoarfrost">
                    {errors.map((e, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 font-mono text-soil">{e.row}</td>
                        <td className="px-3 py-2 font-mono text-soil">{e.column}</td>
                        <td className="px-3 py-2 text-terracotta">{e.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* Step: success */}
          {step === 'success' && (
            <div className="flex flex-col items-center py-6 text-center gap-3">
              <CheckCircle2 size={36} strokeWidth={1.5} className="text-meadow" />
              <p className="font-display italic text-xl text-forest">
                {createdCount} product{createdCount !== 1 ? 's' : ''} created.
              </p>
              <p className="text-sm font-sans text-soil">
                They&apos;re saved as drafts. Publish them from the products list when ready.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-hoarfrost">
          <div>
            {(step === 'preview' || step === 'errors') && (
              <button
                onClick={() => { setStep('pick'); setPreview(null); setFile(null) }}
                className="text-sm font-sans text-soil hover:text-forest transition-colors"
              >
                ← Back
              </button>
            )}
          </div>
          <div className="flex gap-3">
            {step === 'success' ? (
              <button
                onClick={() => { onDone(); onClose() }}
                className="rounded bg-forest px-5 py-2 text-sm font-sans font-medium text-mist hover:bg-meadow transition-colors"
              >
                View products
              </button>
            ) : step === 'preview' ? (
              <>
                <button onClick={onClose} className="text-sm font-sans text-soil hover:text-forest transition-colors">
                  Cancel
                </button>
                <button
                  onClick={() => file && confirmMutation.mutate(file)}
                  disabled={confirmMutation.isPending}
                  className="rounded bg-forest px-5 py-2 text-sm font-sans font-medium text-mist hover:bg-meadow transition-colors disabled:opacity-60"
                >
                  {confirmMutation.isPending ? 'Importing…' : `Import ${preview?.product_count} product${preview?.product_count !== 1 ? 's' : ''}`}
                </button>
              </>
            ) : (
              <button onClick={onClose} className="text-sm font-sans text-soil hover:text-forest transition-colors">
                Cancel
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ProductsPage() {
  const qc = useQueryClient()
  const [openMenu, setOpenMenu] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [showUpload, setShowUpload] = useState(false)

  const { data, isPending } = useQuery({
    queryKey: ['supplier', 'products', page],
    queryFn: getMyProducts,
  })

  const products: Product[] = data?.results ?? []
  const totalCount = data?.count ?? 0

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onDone={() => qc.invalidateQueries({ queryKey: ['supplier', 'products'] })}
        />
      )}

      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display italic text-2xl text-forest">Products</h1>
          <p className="text-sm text-soil font-sans mt-0.5">{totalCount} listing{totalCount !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href={getUploadTemplate()}
            className="inline-flex items-center gap-1.5 text-xs font-sans text-soil hover:text-forest transition-colors border border-hoarfrost rounded px-3 py-2 hover:border-forest"
          >
            <Download size={13} strokeWidth={1.5} />
            Download template
          </a>
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-1.5 border border-hoarfrost text-forest text-xs font-sans font-medium px-3 py-2 rounded hover:border-forest hover:bg-mist/40 transition-colors"
          >
            <Upload size={13} strokeWidth={1.5} />
            Upload products
          </button>
          <button
            onClick={() => alert('Product creation coming soon.')}
            className="flex items-center gap-2 bg-forest text-mist text-xs font-sans font-medium px-4 py-2.5 rounded hover:bg-meadow transition-colors duration-150"
          >
            <Plus className="w-3.5 h-3.5" strokeWidth={2} />
            New product
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
        {isPending ? (
          <div className="px-4 py-12 text-center text-sm font-sans text-soil">Loading products…</div>
        ) : products.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm font-sans text-soil">No products yet. Add your first listing.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Product</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden sm:table-cell">SKU</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium hidden md:table-cell">Category</th>
                  <th className="text-right px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Price</th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">Status</th>
                  <th className="px-4 py-3" aria-label="Actions" />
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {products.map((product) => {
                  const variant = product.variants[0]
                  return (
                    <tr key={product.id} className="hover:bg-mist/50 transition-colors duration-100">
                      <td className="px-4 py-3.5">
                        <p className="text-sm font-sans font-medium text-forest">{product.name}</p>
                      </td>
                      <td className="px-4 py-3.5 hidden sm:table-cell">
                        <span className="font-mono text-xs text-soil">{variant?.sku ?? '—'}</span>
                      </td>
                      <td className="px-4 py-3.5 hidden md:table-cell">
                        <span className="text-xs font-sans text-soil">{product.category_name ?? '—'}</span>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <span className="font-mono text-xs text-forest">£{variant?.price ?? '—'}</span>
                      </td>
                      <td className="px-4 py-3.5"><StatusBadge status={product.status} /></td>
                      <td className="px-4 py-3.5 text-right relative">
                        <button
                          onClick={() => setOpenMenu(openMenu === product.id ? null : product.id)}
                          aria-label="Product actions"
                          className="p-1 rounded hover:bg-mist text-soil hover:text-forest transition-colors duration-100"
                        >
                          <MoreHorizontal className="w-4 h-4" strokeWidth={1.5} />
                        </button>

                        {openMenu === product.id && (
                          <>
                            <div className="fixed inset-0 z-10" onClick={() => setOpenMenu(null)} />
                            <div className="absolute right-4 top-full mt-1 w-44 bg-white border border-hoarfrost rounded-lg shadow-lg z-20 py-1 overflow-hidden">
                              <button
                                onClick={() => { setOpenMenu(null); alert('Edit coming soon.') }}
                                className="w-full text-left px-4 py-2.5 text-xs font-sans text-forest hover:bg-mist transition-colors duration-100"
                              >
                                Edit product
                              </button>
                              <button
                                onClick={() => { setOpenMenu(null); alert('Archive coming soon.') }}
                                className="w-full text-left px-4 py-2.5 text-xs font-sans text-soil hover:bg-mist transition-colors duration-100"
                              >
                                Archive
                              </button>
                            </div>
                          </>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} count={totalCount} onChange={(p) => { setPage(p); setOpenMenu(null) }} />
      </div>
    </div>
  )
}
