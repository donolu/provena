'use client'

import { useState } from 'react'
import { ADMIN_USERS, type AdminUser, type UserRole } from '@/lib/admin-data'

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
  const [users, setUsers]   = useState<AdminUser[]>(ADMIN_USERS)
  const [filter, setFilter] = useState<Tab>('ALL')
  const [search, setSearch] = useState('')

  const displayed = users
    .filter((u) => filter === 'ALL' || u.role === filter)
    .filter((u) =>
      search === '' ||
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase()),
    )

  function toggleActive(id: string) {
    setUsers((prev) => prev.map((u) => u.id === id ? { ...u, is_active: !u.is_active } : u))
  }

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-display italic text-2xl text-forest">Users</h1>
          <p className="text-sm text-soil font-sans mt-0.5">{users.length} registered accounts</p>
        </div>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search name or email…"
          className="text-sm font-sans text-forest placeholder-soil/60 bg-white border border-hoarfrost rounded px-3 py-2 w-56 focus:outline-none focus:border-forest transition-colors"
        />
      </div>

      {/* Role tabs */}
      <div className="border-b border-hoarfrost mb-6 -mx-6 px-6 overflow-x-auto">
        <div className="flex no-scrollbar">
          {TABS.map(({ key, label }) => {
            const count = key === 'ALL' ? users.length : users.filter((u) => u.role === key).length
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
                <span className={`ml-1.5 font-mono text-[10px] ${active ? 'text-soil' : 'text-hoarfrost'}`}>{count}</span>
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
                {['Name', 'Email', 'Role', 'Joined', 'Last active', 'Status', ''].map((h, i) => (
                  <th key={i} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-soil font-sans font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hoarfrost">
              {displayed.map((u) => (
                <tr key={u.id} className="hover:bg-mist/50 transition-colors duration-100">
                  <td className="px-4 py-3.5 text-sm font-sans font-medium text-forest">{u.name}</td>
                  <td className="px-4 py-3.5 font-mono text-xs text-soil">{u.email}</td>
                  <td className="px-4 py-3.5">
                    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-sans font-semibold uppercase tracking-wide ${ROLE_BADGE[u.role]}`}>
                      {u.role.toLowerCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(u.joined_at)}</td>
                  <td className="px-4 py-3.5 text-xs font-sans text-soil whitespace-nowrap">{formatDate(u.last_active_at)}</td>
                  <td className="px-4 py-3.5">
                    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-sans font-semibold uppercase tracking-wide ${u.is_active ? 'bg-meadow/15 text-[#245C38]' : 'bg-hoarfrost text-soil'}`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    {u.role !== 'ADMIN' && (
                      <button
                        onClick={() => toggleActive(u.id)}
                        className="text-xs font-sans text-soil hover:text-forest underline-offset-2 hover:underline transition-colors"
                      >
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {displayed.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-sm font-sans text-soil">
                    No users match your search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
