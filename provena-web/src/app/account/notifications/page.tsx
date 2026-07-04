'use client'

import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell } from 'lucide-react'
import { getNotificationPreferences, updateNotificationPreferences } from '@/lib/api/notifications'
import { useAuthStore } from '@/store/auth'
import type { NotificationPreferences } from '@/lib/api/types'

type PrefKey = keyof Omit<NotificationPreferences, 'updated_at'>

interface PrefRow {
  key: PrefKey
  label: string
  description: string
  audience: 'buyer' | 'supplier' | 'both'
}

const PREFS: PrefRow[] = [
  {
    key: 'email_order_placed',
    label: 'Order confirmed',
    description: 'Email receipt when your payment is taken and order placed.',
    audience: 'buyer',
  },
  {
    key: 'email_order_dispatched',
    label: 'Order dispatched',
    description: 'Notification when a supplier marks your items as shipped.',
    audience: 'buyer',
  },
  {
    key: 'email_new_order',
    label: 'New order received',
    description: 'Alert when a customer places an order from your shop.',
    audience: 'supplier',
  },
  {
    key: 'email_payout_received',
    label: 'Payout processed',
    description: 'Confirmation when a payout has been sent to your bank account.',
    audience: 'supplier',
  },
]

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  disabled: boolean
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={[
        'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-forest focus-visible:ring-offset-1',
        checked ? 'bg-meadow' : 'bg-hoarfrost',
        disabled ? 'opacity-50 cursor-not-allowed' : '',
      ].join(' ')}
    >
      <span
        aria-hidden="true"
        className={[
          'inline-block h-4 w-4 rounded-full bg-white shadow transition-transform duration-200',
          checked ? 'translate-x-4' : 'translate-x-0',
        ].join(' ')}
      />
    </button>
  )
}

export default function NotificationPreferencesPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const qc = useQueryClient()

  const { data: prefs, isPending } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: getNotificationPreferences,
    enabled: !!user,
  })

  const mutation = useMutation({
    mutationFn: (update: Partial<Omit<NotificationPreferences, 'updated_at'>>) =>
      updateNotificationPreferences(update),
    onSuccess: (data) => {
      qc.setQueryData(['notification-preferences'], data)
    },
  })

  if (!user) {
    router.push('/login')
    return null
  }

  function handleToggle(key: PrefKey, value: boolean) {
    mutation.mutate({ [key]: value })
  }

  return (
    <div className="min-h-screen bg-mist">
      <div className="max-w-xl mx-auto px-6 py-12">
        <div className="flex items-center gap-3 mb-8">
          <Bell size={20} strokeWidth={1.5} className="text-forest" />
          <div>
            <h1 className="font-display italic text-2xl text-forest">Email notifications</h1>
            <p className="text-xs font-sans text-soil mt-0.5">
              Choose which emails Provena sends to <strong>{user.email}</strong>.
            </p>
          </div>
        </div>

        {isPending ? (
          <div className="text-sm font-sans text-soil text-center py-12">Loading preferences…</div>
        ) : (
          <div className="bg-white rounded-xl border border-hoarfrost overflow-hidden divide-y divide-hoarfrost">
            {PREFS.map((pref) => (
              <div key={pref.key} className="flex items-start gap-4 px-5 py-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-sans font-medium text-forest">{pref.label}</p>
                  <p className="text-xs font-sans text-soil mt-0.5 leading-relaxed">{pref.description}</p>
                </div>
                <div className="pt-0.5 flex-shrink-0">
                  {prefs ? (
                    <Toggle
                      checked={prefs[pref.key]}
                      onChange={(v) => handleToggle(pref.key, v)}
                      disabled={mutation.isPending}
                    />
                  ) : (
                    <div className="h-5 w-9 rounded-full bg-hoarfrost" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        <p className="text-[10px] font-sans text-soil/60 mt-5 leading-relaxed text-center">
          Account security emails (password resets, login alerts) are always sent regardless of these settings.
        </p>
      </div>
    </div>
  )
}
