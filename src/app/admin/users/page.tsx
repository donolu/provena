'use client'

import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, X } from 'lucide-react'
import { getAdminUsers, suspendUser, activateUser, deleteUser } from '@/lib/api/admin'
import { Pagination } from '@/components/pagination'
import type { AdminUser, UserRole } from '@/lib/api/types'

type Tab = 'ALL' | UserRole

const TABS: { key: Tab; label: string }[] = [
  { key: 'ALL',      label: 'All' },
  { key: 'BUYER',    label: 'Buyers' },
  { key: 'SUPPLIER', label: 'Suppliers' },
  { key: 'ADMIN',    label: 'Admins' },
]

const ROLE_BADGE: Record<UserRole, string> = {
  BUYER:    'bg-forest/8 text-forest',
  SUPPLIER: 'bg-meadow/15 text-[#245C38]',
  ADMIN:    'bg-marigold/15 text-[#7A5A08]',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function UsersPage() {
  const [filter, setFilter]             = useState<Tab>('ALL')
  const [search, setSearch]             = useState('')
  const [debouncedSearch, setDebounced] = useState('')
  const [page, setPage]                 = useState(1)
  const [deleteTarget, setDeleteTarget] = useState<AdminUser | null>(null)
  const debounceRef                     = useRef<ReturnType<typeof setTimeout> | null>(null)
  const qc                              = useQueryClient()

  function handleSearchChange(val: string) {
    setSearch(val)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setDebounced(val)
      setPage(1)
    }, 300)
  }

  const { data, isPending } = useQuery({
    queryKey: ['admin', 'users', filter, debouncedSearch, page],
    queryFn: () => getAdminUsers({
      role: filter === 'ALL' ? undefined : filter,
      q: debouncedSearch || undefined,
      page,
    }),
  })

  const toggleMutation = useMutation({
    mutationFn: (user: AdminUser) =>
      user.is_active ? suspendUser(user.id) : activateUser(user.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] })
      setDeleteTarget(null)
    },
  })

  const users = data?.results ?? []
  const totalCount = data?.count ?? 0

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-display italic text-2xl text-forest">Users</h1>
          <p className="text-sm text-soil font-sans mt-0.5">{totalCount} registered account{totalCount !== 1 ? 's' : ''}</p>
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-soil/60 pointer-events-none" />
          <input
            type="search"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search name or email…"
            className="pl-8 pr-8 py-2 text-sm font-sans text-forest placeholder-soil/60 bg-white border border-hoarfrost rounded w-56 focus:outline-none focus:border-forest transition-colors"
          />
          {search && (
            <button
              onClick={() => handleSearchChange('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-soil/60 hover:text-forest"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      <div className="border-b border-hoarfrost mb-6 -mx-6 px-6 overflow-x-auto">
        <div className="flex no-scrollbar">
          {TABS.map(({ key, label }) => {
            const active = filter === key
            return (
              <button
                key={key}
                onClick={() => { setFilter(key); setPage(1) }}
                className={[
                  'relative flex-shrink-0 px-4 py-3 text-xs font-sans whitespace-nowrap transition-colors duration-150',
                  active ? 'text-forest font-medium' : 'text-soil hover:text-forest',
                ].join(' ')}
              >
                {label}
                {active && <span className="absolute bottom-0 left-4 right-4 h-0.5 bg-forest rounded-full" />}
              </button>
            )
          })}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
        {isPending ? (
          <div className="px-4 py-12 text-center text-sm font-sans text-soil">Loading users…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  {['Name', 'Email', 'Role', 'Joined', 'Status', ''].map((h, i) => (
                    <th key={i} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3.5 text-sm font-sans font-medium text-forest">
                      {[u.first_name, u.last_name].filter(Boolean).join(' ') || '-'}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-soil">{u.email}</td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-sans font-semibold uppercase tracking-wide ${ROLE_BADGE[u.role]}`}>
                        {u.role.toLowerCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(u.created_at)}</td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-sans font-semibold uppercase tracking-wide ${u.is_active ? 'bg-meadow/15 text-[#245C38]' : 'bg-hoarfrost text-soil'}`}>
                        {u.is_active ? 'Active' : 'Suspended'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      {!u.is_staff && (
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => toggleMutation.mutate(u)}
                            disabled={toggleMutation.isPending}
                            className="text-xs font-sans text-soil hover:text-forest underline-offset-2 hover:underline transition-colors disabled:opacity-40"
                          >
                            {u.is_active ? 'Suspend' : 'Activate'}
                          </button>
                          <button
                            onClick={() => setDeleteTarget(u)}
                            className="text-xs font-sans text-red-500 hover:text-red-700 underline-offset-2 hover:underline transition-colors"
                          >
                            Delete
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-sm font-sans text-soil">
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} count={totalCount} onChange={setPage} />
      </div>

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h2 className="font-display italic text-xl text-forest mb-2">Delete account?</h2>
            <p className="text-sm font-sans text-soil mb-1">
              This will permanently delete <span className="text-forest font-medium">{deleteTarget.email}</span>.
            </p>
            <p className="text-xs font-sans text-soil/70 mb-6">This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 text-sm font-sans text-soil hover:text-forest border border-hoarfrost rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm font-sans text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-40"
              >
                {deleteMutation.isPending ? 'Deleting…' : 'Delete account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
