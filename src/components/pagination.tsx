'use client'

import { ChevronLeft, ChevronRight } from 'lucide-react'

interface Props {
  page: number
  count: number
  pageSize?: number
  onChange: (page: number) => void
}

export function Pagination({ page, count, pageSize = 20, onChange }: Props) {
  const totalPages = Math.ceil(count / pageSize)
  if (totalPages <= 1) return null

  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, count)

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-hoarfrost">
      <p className="text-xs font-sans text-soil">
        {from}–{to} of {count}
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page === 1}
          aria-label="Previous page"
          className="p-1.5 rounded hover:bg-mist text-soil hover:text-forest disabled:opacity-30 disabled:cursor-not-allowed transition-colors duration-100"
        >
          <ChevronLeft className="w-3.5 h-3.5" strokeWidth={2} />
        </button>
        <span className="px-2 font-mono text-xs text-forest">
          {page} / {totalPages}
        </span>
        <button
          onClick={() => onChange(page + 1)}
          disabled={page === totalPages}
          aria-label="Next page"
          className="p-1.5 rounded hover:bg-mist text-soil hover:text-forest disabled:opacity-30 disabled:cursor-not-allowed transition-colors duration-100"
        >
          <ChevronRight className="w-3.5 h-3.5" strokeWidth={2} />
        </button>
      </div>
    </div>
  )
}
