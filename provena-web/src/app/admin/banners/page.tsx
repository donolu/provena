'use client'

import { useState } from 'react'
import NextImage from 'next/image'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Image as ImageIcon, Plus, Pencil, Trash2, ToggleLeft, ToggleRight } from 'lucide-react'
import { getBanners, createBanner, updateBanner, deleteBanner } from '@/lib/api/admin'
import type { Banner } from '@/lib/api/types'

interface BannerFormValues {
  title: string
  subtitle: string
  image_url: string
  link: string
  is_active: boolean
  position: number
}

const EMPTY: BannerFormValues = { title: '', subtitle: '', image_url: '', link: '', is_active: true, position: 0 }

function BannerModal({
  initial,
  onSave,
  onClose,
  saving,
}: {
  initial: BannerFormValues
  onSave: (v: BannerFormValues) => void
  onClose: () => void
  saving: boolean
}) {
  const [form, setForm] = useState(initial)
  const set = (k: keyof BannerFormValues, v: string | boolean | number) =>
    setForm((f) => ({ ...f, [k]: v }))

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4">
        <h2 className="font-display italic text-xl text-forest">
          {initial.title ? 'Edit banner' : 'New banner'}
        </h2>

        <div className="space-y-3">
          <label className="block">
            <span className="text-xs font-sans text-soil">Title</span>
            <input
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
              className="mt-1 w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-forest/30"
            />
          </label>
          <label className="block">
            <span className="text-xs font-sans text-soil">Subtitle</span>
            <textarea
              value={form.subtitle}
              onChange={(e) => set('subtitle', e.target.value)}
              rows={2}
              className="mt-1 w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-forest/30 resize-none"
            />
          </label>
          <label className="block">
            <span className="text-xs font-sans text-soil">Image URL</span>
            <input
              type="url"
              value={form.image_url}
              onChange={(e) => set('image_url', e.target.value)}
              className="mt-1 w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-forest/30"
            />
          </label>
          <label className="block">
            <span className="text-xs font-sans text-soil">Link (optional)</span>
            <input
              type="url"
              value={form.link}
              onChange={(e) => set('link', e.target.value)}
              placeholder="https://"
              className="mt-1 w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-forest/30"
            />
          </label>
          <div className="flex items-center gap-6">
            <label className="block">
              <span className="text-xs font-sans text-soil">Position</span>
              <input
                type="number"
                min={0}
                value={form.position}
                onChange={(e) => set('position', parseInt(e.target.value, 10) || 0)}
                className="mt-1 w-20 px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-forest/30"
              />
            </label>
            <label className="flex items-center gap-2 cursor-pointer mt-4">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => set('is_active', e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-sans text-forest">Active</span>
            </label>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm font-sans text-soil hover:text-forest transition-colors">
            Cancel
          </button>
          <button
            onClick={() => onSave(form)}
            disabled={saving || !form.title.trim() || !form.image_url.trim()}
            className="px-4 py-2 bg-forest text-white text-sm font-sans rounded-lg hover:bg-forest/90 disabled:opacity-60 transition-colors"
          >
            {saving ? 'Saving…' : 'Save banner'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function AdminBannersPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState<{ banner?: Banner } | null>(null)

  const { data, isLoading } = useQuery({ queryKey: ['admin', 'banners'], queryFn: getBanners })
  const banners = data?.results ?? []

  const createMut = useMutation({
    mutationFn: createBanner,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'banners'] }); setModal(null) },
  })

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateBanner>[1] }) =>
      updateBanner(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'banners'] }); setModal(null) },
  })

  const deleteMut = useMutation({
    mutationFn: deleteBanner,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'banners'] }),
  })

  function handleSave(values: BannerFormValues) {
    if (modal?.banner) {
      updateMut.mutate({ id: modal.banner.id, payload: values })
    } else {
      createMut.mutate(values)
    }
  }

  const saving = createMut.isPending || updateMut.isPending

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <ImageIcon className="h-5 w-5 text-marigold" />
          <h1 className="font-display italic text-2xl text-forest">Banners</h1>
        </div>
        <button
          onClick={() => setModal({})}
          className="inline-flex items-center gap-2 px-4 py-2 bg-forest text-white text-sm font-sans rounded-lg hover:bg-forest/90 transition-colors"
        >
          <Plus className="h-4 w-4" /> New banner
        </button>
      </div>

      {isLoading && (
        <div className="text-sm font-sans text-soil animate-pulse">Loading…</div>
      )}

      {!isLoading && banners.length === 0 && (
        <div className="text-center py-16 text-soil">
          <ImageIcon className="h-8 w-8 mx-auto mb-3 opacity-30" />
          <p className="text-sm font-sans">No banners yet. Create one to feature content on the homepage.</p>
        </div>
      )}

      {banners.length > 0 && (
        <div className="space-y-3">
          {banners.map((banner) => (
            <div key={banner.id} className="bg-white border border-stone-200 rounded-xl p-4 flex items-center gap-4">
              {banner.image_url && (
                <NextImage
                  src={banner.image_url}
                  alt={banner.title}
                  width={80}
                  height={48}
                  className="object-cover rounded-lg shrink-0"
                />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-sans font-medium text-forest truncate">{banner.title}</p>
                {banner.subtitle && (
                  <p className="text-xs font-sans text-soil truncate">{banner.subtitle}</p>
                )}
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs font-sans text-stone-400">Position {banner.position}</span>
                  {banner.link && (
                    <a href={banner.link} target="_blank" rel="noopener noreferrer" className="text-xs font-sans text-forest underline underline-offset-2 truncate max-w-xs">
                      {banner.link}
                    </a>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => updateMut.mutate({ id: banner.id, payload: { is_active: !banner.is_active } })}
                  title={banner.is_active ? 'Deactivate' : 'Activate'}
                  className="p-1.5 rounded hover:bg-stone-100 transition-colors"
                >
                  {banner.is_active
                    ? <ToggleRight className="h-5 w-5 text-green-600" />
                    : <ToggleLeft className="h-5 w-5 text-stone-400" />}
                </button>
                <button
                  onClick={() => setModal({ banner })}
                  className="p-1.5 rounded hover:bg-stone-100 transition-colors"
                >
                  <Pencil className="h-4 w-4 text-soil" />
                </button>
                <button
                  onClick={() => { if (confirm('Delete this banner?')) deleteMut.mutate(banner.id) }}
                  className="p-1.5 rounded hover:bg-red-50 transition-colors"
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {modal && (
        <BannerModal
          initial={modal.banner
            ? { title: modal.banner.title, subtitle: modal.banner.subtitle, image_url: modal.banner.image_url, link: modal.banner.link, is_active: modal.banner.is_active, position: modal.banner.position }
            : EMPTY}
          onSave={handleSave}
          onClose={() => setModal(null)}
          saving={saving}
        />
      )}
    </div>
  )
}
