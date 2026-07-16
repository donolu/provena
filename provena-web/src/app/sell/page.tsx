'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useMutation } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { Store, PackageCheck, Wallet, ArrowRight, CheckCircle2 } from 'lucide-react'
import { registerSupplier, type SupplierRegistrationPayload } from '@/lib/api/suppliers'
import { getMe } from '@/lib/api/auth'
import { useAuthStore } from '@/store/auth'

const BENEFITS = [
  {
    icon: Store,
    title: 'Reach vetted buyers',
    desc: 'List alongside trusted UK suppliers on a marketplace buyers already shop.',
  },
  {
    icon: PackageCheck,
    title: 'Run it from one place',
    desc: 'Manage products, inventory, orders and returns in a single dashboard.',
  },
  {
    icon: Wallet,
    title: 'Get paid securely',
    desc: 'Payouts settle straight to your bank through Stripe Connect.',
  },
]

const STEPS = [
  'Tell us about your business',
  'Verify your identity and turn on two-factor authentication',
  'Connect Stripe to receive payouts',
  'List your products and start selling',
]

const labelClass =
  'block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5'
const inputClass =
  'w-full border border-stone-300 rounded-lg px-3 py-2 text-sm text-forest focus:outline-none focus:ring-2 focus:ring-forest/30'

function extractError(e: unknown): string {
  const err = e as AxiosError<{
    error?: { message?: string }
    business_name?: string[]
    detail?: string
  }>
  const data = err.response?.data
  return (
    data?.error?.message ??
    data?.business_name?.[0] ??
    data?.detail ??
    'Something went wrong. Please check the form and try again.'
  )
}

export default function SellPage() {
  const user = useAuthStore((s) => s.user)
  const isInitialised = useAuthStore((s) => s.isInitialised)
  const setUser = useAuthStore((s) => s.setUser)

  const [form, setForm] = useState({
    business_name: '',
    description: '',
    phone: '',
    website: '',
    logo_url: '',
  })
  const [addr, setAddr] = useState({
    line1: '',
    line2: '',
    city: '',
    county: '',
    postcode: '',
    country: 'GB',
  })
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((f) => ({ ...f, [k]: e.target.value }))
    setError('')
  }
  const setAddress = (k: keyof typeof addr) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setAddr((a) => ({ ...a, [k]: e.target.value }))
  }

  const mutation = useMutation({
    mutationFn: () => {
      const payload: SupplierRegistrationPayload = {
        business_name: form.business_name.trim(),
        description: form.description.trim() || undefined,
        phone: form.phone.trim() || undefined,
        website: form.website.trim() || undefined,
        logo_url: form.logo_url.trim() || undefined,
      }
      // Address is optional; only send it once the required parts are filled in.
      if (addr.line1.trim() && addr.city.trim() && addr.postcode.trim()) {
        payload.address = {
          line1: addr.line1.trim(),
          line2: addr.line2.trim() || undefined,
          city: addr.city.trim(),
          county: addr.county.trim() || undefined,
          postcode: addr.postcode.trim(),
          country: addr.country.trim() || 'GB',
        }
      }
      return registerSupplier(payload)
    },
    onSuccess: async () => {
      // The user is now a SUPPLIER; refresh the profile so the store and the
      // route-gating cookies reflect the new role before they reach /supplier.
      try {
        const profile = await getMe()
        setUser(profile)
      } catch {
        // Non-fatal: the profile refresh is a convenience; the account is created.
      }
      setDone(true)
    },
    onError: (e) => setError(extractError(e)),
  })

  return (
    <div className="min-h-screen bg-mist">
      {/* Hero */}
      <section className="bg-forest text-mist">
        <div className="max-w-6xl mx-auto px-6 py-16 grid lg:grid-cols-2 gap-12 items-start">
          <div>
            <span className="text-[11px] uppercase tracking-[0.16em] text-marigold font-sans">
              For suppliers
            </span>
            <h1 className="font-display italic text-4xl md:text-5xl text-mist mt-3 mb-4 text-balance">
              Sell on Provena
            </h1>
            <p className="text-mist/80 font-sans leading-relaxed max-w-md">
              Bring your products to a UK marketplace built on provenance and trust. Apply in
              minutes; once your business is verified you can list, sell and get paid.
            </p>

            <ul className="mt-8 space-y-5">
              {BENEFITS.map(({ icon: Icon, title, desc }) => (
                <li key={title} className="flex items-start gap-3">
                  <Icon className="h-5 w-5 text-marigold mt-0.5 shrink-0" />
                  <span>
                    <span className="block text-sm font-sans font-semibold text-mist">{title}</span>
                    <span className="block text-sm text-mist/70 font-sans">{desc}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Action panel */}
          <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8 text-forest">
            <Panel
              isInitialised={isInitialised}
              role={user?.role}
              done={done}
              error={error}
              form={form}
              addr={addr}
              set={set}
              setAddress={setAddress}
              pending={mutation.isPending}
              onSubmit={() => mutation.mutate()}
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="font-display italic text-2xl text-forest mb-8">How it works</h2>
        <ol className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <li key={step} className="relative">
              <span className="font-display italic text-3xl text-marigold">{i + 1}</span>
              <p className="mt-2 text-sm font-sans text-soil leading-relaxed">{step}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}

interface PanelProps {
  isInitialised: boolean
  role?: string
  done: boolean
  error: string
  form: { business_name: string; description: string; phone: string; website: string; logo_url: string }
  addr: { line1: string; line2: string; city: string; county: string; postcode: string; country: string }
  set: (k: 'business_name' | 'description' | 'phone' | 'website' | 'logo_url') => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void
  setAddress: (k: 'line1' | 'line2' | 'city' | 'county' | 'postcode' | 'country') => (e: React.ChangeEvent<HTMLInputElement>) => void
  pending: boolean
  onSubmit: () => void
}

function Panel({ isInitialised, role, done, error, form, addr, set, setAddress, pending, onSubmit }: PanelProps) {
  if (done) {
    return (
      <div className="text-center py-4">
        <CheckCircle2 className="h-10 w-10 text-green-600 mx-auto mb-4" />
        <h2 className="font-display italic text-xl text-forest mb-2">Application received</h2>
        <p className="text-sm font-sans text-soil leading-relaxed mb-6">
          Your supplier profile is pending review. Next, set up two-factor authentication and
          connect Stripe from your dashboard, and our team will verify your business.
        </p>
        <Link
          href="/supplier/dashboard"
          className="inline-flex items-center gap-2 px-4 py-2 bg-forest text-white text-sm font-sans rounded-lg hover:bg-forest/90 transition-colors"
        >
          Go to your dashboard <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    )
  }

  if (!isInitialised) {
    return <p className="text-sm font-sans text-soil py-8 text-center">Loading…</p>
  }

  if (!role) {
    return (
      <div className="py-2">
        <h2 className="font-display italic text-xl text-forest mb-2">Start your application</h2>
        <p className="text-sm font-sans text-soil leading-relaxed mb-6">
          You need a Provena account to sell. Log in or sign up, then come back to apply.
        </p>
        <div className="flex flex-col gap-3">
          <Link
            href="/login?next=/sell"
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-forest text-white text-sm font-sans rounded-lg hover:bg-forest/90 transition-colors"
          >
            Log in to apply <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/register?next=/sell"
            className="inline-flex items-center justify-center px-4 py-2.5 border border-stone-300 text-forest text-sm font-sans rounded-lg hover:border-forest/40 transition-colors"
          >
            Create an account
          </Link>
        </div>
      </div>
    )
  }

  if (role === 'SUPPLIER') {
    return (
      <div className="text-center py-4">
        <Store className="h-10 w-10 text-marigold mx-auto mb-4" />
        <h2 className="font-display italic text-xl text-forest mb-2">You already sell on Provena</h2>
        <p className="text-sm font-sans text-soil leading-relaxed mb-6">
          Manage your products, orders and payouts from your supplier dashboard.
        </p>
        <Link
          href="/supplier/dashboard"
          className="inline-flex items-center gap-2 px-4 py-2 bg-forest text-white text-sm font-sans rounded-lg hover:bg-forest/90 transition-colors"
        >
          Go to your dashboard <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    )
  }

  if (role === 'ADMIN') {
    return (
      <div className="text-center py-4">
        <h2 className="font-display italic text-xl text-forest mb-2">You&apos;re signed in as an admin</h2>
        <p className="text-sm font-sans text-soil leading-relaxed mb-6">
          Suppliers are reviewed and managed from the admin area.
        </p>
        <Link
          href="/admin/suppliers"
          className="inline-flex items-center gap-2 px-4 py-2 bg-forest text-white text-sm font-sans rounded-lg hover:bg-forest/90 transition-colors"
        >
          Manage suppliers <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    )
  }

  // Buyer: the registration form.
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
      className="space-y-4"
    >
      <h2 className="font-display italic text-xl text-forest">Tell us about your business</h2>

      <div>
        <label className={labelClass} htmlFor="business_name">
          Business name *
        </label>
        <input
          id="business_name"
          value={form.business_name}
          onChange={set('business_name')}
          required
          className={inputClass}
        />
      </div>

      <div>
        <label className={labelClass} htmlFor="description">
          What you sell
        </label>
        <textarea
          id="description"
          value={form.description}
          onChange={set('description')}
          rows={3}
          className={inputClass}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelClass} htmlFor="phone">
            Phone
          </label>
          <input id="phone" value={form.phone} onChange={set('phone')} autoComplete="tel" className={inputClass} />
        </div>
        <div>
          <label className={labelClass} htmlFor="website">
            Website
          </label>
          <input
            id="website"
            type="url"
            value={form.website}
            onChange={set('website')}
            placeholder="https://"
            className={inputClass}
          />
        </div>
      </div>

      <details className="group">
        <summary className="cursor-pointer text-[11px] uppercase tracking-[0.12em] text-soil font-sans list-none flex items-center gap-2">
          <span className="text-marigold group-open:rotate-90 transition-transform">›</span>
          Business address (optional)
        </summary>
        <div className="mt-3 space-y-3">
          <input placeholder="Address line 1" value={addr.line1} onChange={setAddress('line1')} className={inputClass} />
          <input placeholder="Address line 2" value={addr.line2} onChange={setAddress('line2')} className={inputClass} />
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="City" value={addr.city} onChange={setAddress('city')} className={inputClass} />
            <input placeholder="County" value={addr.county} onChange={setAddress('county')} className={inputClass} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Postcode" value={addr.postcode} onChange={setAddress('postcode')} className={inputClass} />
            <input placeholder="Country" value={addr.country} onChange={setAddress('country')} className={inputClass} />
          </div>
        </div>
      </details>

      {error && <p className="text-sm text-red-600 font-sans">{error}</p>}

      <button
        type="submit"
        disabled={pending || !form.business_name.trim()}
        className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-forest text-white text-sm font-sans rounded-lg hover:bg-forest/90 disabled:opacity-60 transition-colors"
      >
        {pending ? 'Submitting…' : 'Submit application'}
        {!pending && <ArrowRight className="h-4 w-4" />}
      </button>
      <p className="text-xs text-soil/70 font-sans text-center">
        Your account is upgraded to a supplier and reviewed before you can list.
      </p>
    </form>
  )
}
