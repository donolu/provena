'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Star, Trash2 } from 'lucide-react'
import { getAdminReviews, adminApproveReview, adminDeleteReview } from '@/lib/api/admin'
import type { Review } from '@/lib/api/types'

type Tab = 'PENDING' | 'APPROVED'

function StarDisplay({ value }: { value: number }) {
  return (
    <span className="flex items-center gap-0.5" aria-label={`${value} stars`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={`w-3 h-3 ${i < value ? 'fill-marigold text-marigold' : 'text-hoarfrost'}`}
          strokeWidth={1.5}
        />
      ))}
    </span>
  )
}

function ReviewRow({ review, onApprove, onDelete }: {
  review: Review
  onApprove?: () => void
  onDelete: () => void
}) {
  return (
    <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
      <div className="px-5 py-3.5 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StarDisplay value={review.rating} />
            {review.is_verified_purchase && (
              <span className="text-[10px] font-sans text-meadow font-medium bg-meadow/10 px-1.5 py-0.5 rounded-full">
                Verified purchase
              </span>
            )}
          </div>
          <p className="text-xs font-sans font-semibold text-forest">{review.title}</p>
          <p className="text-[11px] font-sans text-soil mt-0.5">
            {review.reviewer_email ?? 'Anonymous'} · SKU {review.variant_sku} ·{' '}
            {new Date(review.created_at).toLocaleDateString('en-GB', {
              day: 'numeric', month: 'short', year: 'numeric',
            })}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {onApprove && (
            <button
              onClick={onApprove}
              className="flex items-center gap-1.5 text-xs font-sans text-meadow hover:text-forest transition-colors"
            >
              <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
              Approve
            </button>
          )}
          <button
            onClick={onDelete}
            className="flex items-center gap-1.5 text-xs font-sans text-red-500 hover:text-red-700 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
            Delete
          </button>
        </div>
      </div>
      <div className="px-5 pb-4 border-t border-hoarfrost pt-3">
        <p className="text-xs font-sans text-soil leading-relaxed">{review.body}</p>
      </div>
    </div>
  )
}

export default function AdminReviewsPage() {
  const [tab, setTab] = useState<Tab>('PENDING')
  const qc = useQueryClient()

  const { data: reviews = [], isPending } = useQuery({
    queryKey: ['admin', 'reviews', tab],
    queryFn: () => getAdminReviews({ is_approved: tab === 'APPROVED' }),
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => adminApproveReview(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'reviews'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminDeleteReview(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'reviews'] })
    },
  })

  const pendingCount = tab === 'PENDING' ? reviews.length : null

  return (
    <div className="px-6 py-8 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display italic text-2xl text-forest">Reviews</h1>
        <p className="text-sm text-soil font-sans mt-0.5">
          {isPending ? 'Loading…' : `${reviews.length} review${reviews.length !== 1 ? 's' : ''}${pendingCount !== null ? ' awaiting approval' : ''}`}
        </p>
      </div>

      <div className="flex items-center gap-1 mb-6">
        {(['PENDING', 'APPROVED'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-xs font-sans rounded-full border transition-colors ${
              tab === t
                ? 'bg-forest text-white border-forest'
                : 'bg-white text-soil border-hoarfrost hover:border-forest hover:text-forest'
            }`}
          >
            {t === 'PENDING' ? 'Awaiting approval' : 'Approved'}
          </button>
        ))}
      </div>

      {isPending ? (
        <p className="text-sm font-sans text-soil">Loading…</p>
      ) : reviews.length === 0 ? (
        <p className="text-sm font-sans text-soil">
          {tab === 'PENDING' ? 'No reviews awaiting approval.' : 'No approved reviews.'}
        </p>
      ) : (
        <div className="space-y-3">
          {reviews.map((review) => (
            <ReviewRow
              key={review.id}
              review={review}
              onApprove={tab === 'PENDING' ? () => approveMutation.mutate(review.id) : undefined}
              onDelete={() => deleteMutation.mutate(review.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
