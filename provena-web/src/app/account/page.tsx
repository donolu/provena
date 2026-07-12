'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useMutation } from '@tanstack/react-query'
import { User as UserIcon, MapPin, ShieldCheck, Bell, CreditCard, Package, Heart } from 'lucide-react'
import { updateMe, getMe } from '@/lib/api/auth'
import { useAuthStore } from '@/store/auth'

const LINKS = [
  { href: '/account/addresses', label: 'Addresses', desc: 'Delivery addresses', icon: MapPin },
  { href: '/account/security', label: 'Security', desc: 'Password and 2FA', icon: ShieldCheck },
  { href: '/account/notifications', label: 'Notifications', desc: 'Email preferences', icon: Bell },
  { href: '/account/payments', label: 'Payments', desc: 'Payment history', icon: CreditCard },
  { href: '/orders', label: 'Orders', desc: 'Your order history', icon: Package },
  { href: '/wishlist', label: 'Wishlist', desc: 'Saved items', icon: Heart },
]

export default function AccountPage() {
  const { user, setUser } = useAuthStore()
  const [firstName, setFirstName] = useState(user?.first_name ?? '')
  const [lastName, setLastName] = useState(user?.last_name ?? '')
  const [saved, setSaved] = useState(false)

  const mutation = useMutation({
    mutationFn: () => updateMe({ first_name: firstName, last_name: lastName }),
    onSuccess: async () => {
      const profile = await getMe()
      setUser(profile)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    },
  })

  const dirty = firstName !== (user?.first_name ?? '') || lastName !== (user?.last_name ?? '')

  return (
    <div className="max-w-xl mx-auto px-6 py-10">
      <div className="flex items-center gap-3 mb-8">
        <UserIcon className="h-5 w-5 text-marigold" />
        <h1 className="font-display italic text-2xl text-forest">Your account</h1>
      </div>

      <div className="bg-white border border-stone-200 rounded-xl p-6">
        <h2 className="font-sans font-semibold text-forest text-sm mb-5">Profile</h2>
        <form
          onSubmit={(e) => { e.preventDefault(); mutation.mutate() }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">First name</label>
              <input
                value={firstName}
                onChange={(e) => { setFirstName(e.target.value); setSaved(false) }}
                autoComplete="given-name"
                className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm text-forest focus:outline-none focus:ring-2 focus:ring-forest/30"
              />
            </div>
            <div>
              <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">Last name</label>
              <input
                value={lastName}
                onChange={(e) => { setLastName(e.target.value); setSaved(false) }}
                autoComplete="family-name"
                className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm text-forest focus:outline-none focus:ring-2 focus:ring-forest/30"
              />
            </div>
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">Email</label>
            <input
              value={user?.email ?? ''}
              readOnly
              className="w-full border border-stone-200 bg-stone-50 rounded-lg px-3 py-2 text-sm text-soil cursor-not-allowed"
            />
            <p className="mt-1 text-xs text-soil/70">Contact support to change your email address.</p>
          </div>

          <div className="flex items-center gap-3 pt-1">
            <button
              type="submit"
              disabled={mutation.isPending || !dirty}
              className="px-4 py-2 bg-forest text-white text-sm font-sans rounded-lg hover:bg-forest/90 disabled:opacity-60 transition-colors"
            >
              {mutation.isPending ? 'Saving…' : 'Save changes'}
            </button>
            {saved && <span className="text-xs font-sans text-green-700">Saved</span>}
            {mutation.isError && <span className="text-xs font-sans text-red-600">Could not save. Try again.</span>}
          </div>
        </form>
      </div>

      <div className="grid grid-cols-2 gap-3 mt-6">
        {LINKS.map(({ href, label, desc, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="flex items-start gap-3 bg-white border border-stone-200 rounded-xl p-4 hover:border-forest/40 transition-colors"
          >
            <Icon className="h-4 w-4 text-marigold mt-0.5 shrink-0" />
            <span>
              <span className="block text-sm font-sans font-semibold text-forest">{label}</span>
              <span className="block text-xs text-soil">{desc}</span>
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}
