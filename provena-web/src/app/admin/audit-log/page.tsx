'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Shield } from 'lucide-react'
import { getAuditLog } from '@/lib/api/admin'
import { Pagination } from '@/components/pagination'

const ACTION_LABELS: Record<string, string> = {
  'supplier.approved':  'Supplier approved',
  'supplier.suspended': 'Supplier suspended',
  'supplier.rejected':  'Supplier rejected',
  'user.suspended':     'User suspended',
  'user.activated':     'User activated',
  'payment.refunded':   'Payment refunded',
}

const ACTION_COLOURS: Record<string, string> = {
  'supplier.approved':  'bg-green-100 text-green-800',
  'supplier.suspended': 'bg-amber-100 text-amber-800',
  'supplier.rejected':  'bg-red-100 text-red-800',
  'user.suspended':     'bg-amber-100 text-amber-800',
  'user.activated':     'bg-green-100 text-green-800',
  'payment.refunded':   'bg-blue-100 text-blue-800',
}

export default function AuditLogPage() {
  const [page, setPage] = useState(1)
  const [actionFilter, setActionFilter] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'audit-log', page, actionFilter],
    queryFn: () => getAuditLog({ page, action: actionFilter || undefined }),
  })

  const entries = data?.results ?? []

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-forest">Audit log</h1>
          <p className="text-sm text-gray-500 mt-0.5">Admin actions recorded automatically.</p>
        </div>

        <input
          type="text"
          placeholder="Filter by action..."
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1) }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm w-52 focus:outline-none focus:ring-2 focus:ring-forest"
        />
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 animate-pulse rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && entries.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Shield className="h-10 w-10 text-gray-300 mb-4" />
          <p className="font-medium text-gray-700">No audit entries yet</p>
          <p className="text-sm text-gray-500 mt-1">
            Admin actions will appear here as they are performed.
          </p>
        </div>
      )}

      {!isLoading && entries.length > 0 && (
        <>
          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b text-xs font-semibold uppercase tracking-wide text-gray-500 text-left">
                  <th className="px-4 py-3">When</th>
                  <th className="px-4 py-3">Actor</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {new Date(entry.created_at).toLocaleString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="px-4 py-3 text-xs font-medium text-gray-700">
                      {entry.actor_email ?? 'system'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          ACTION_COLOURS[entry.action] ?? 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {ACTION_LABELS[entry.action] ?? entry.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {entry.target_type && (
                        <span className="font-medium text-gray-700">{entry.target_type} </span>
                      )}
                      {entry.target_id && (
                        <span className="font-mono">{entry.target_id.slice(0, 8)}&hellip;</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data && data.count > 20 && (
            <div className="mt-4">
              <Pagination
                page={page}
                count={data.count}
                onChange={setPage}
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}
