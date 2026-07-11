'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { register } from '@/lib/api/auth'
import { mergeGuestCart } from '@/lib/api/cart'
import { safeNext } from '@/lib/navigation'
import { useAuthStore } from '@/store/auth'

function RegisterForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login: storeLogin } = useAuthStore()

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName]   = useState('')
  const [email, setEmail]         = useState('')
  const [password, setPassword]   = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError]         = useState('')
  const [loading, setLoading]     = useState(false)

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (password !== passwordConfirm) {
      setError('Passwords do not match.')
      return
    }
    if (password.length < 12) {
      setError('Password must be at least 12 characters.')
      return
    }

    setLoading(true)
    try {
      const { access, user } = await register({
        email,
        password,
        password_confirm: passwordConfirm,
        first_name: firstName,
        last_name: lastName,
      })
      await mergeGuestCart(access).catch(() => {})
      storeLogin(user, access)
      router.push(safeNext(searchParams.get('next'), '/catalogue'))
    } catch (err: unknown) {
      const data = (err as {
        response?: { data?: Record<string, unknown> & { error?: { message?: string }; detail?: string } }
      }).response?.data
      let msg = data?.error?.message ?? data?.detail
      if (!msg && data && typeof data === 'object') {
        const first = Object.values(data)[0]
        msg = Array.isArray(first) ? String(first[0]) : typeof first === 'string' ? first : undefined
      }
      setError(msg ?? 'Could not create your account. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-mist flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <Link href="/catalogue" className="block font-display italic text-2xl text-forest text-center mb-10">
          Provena
        </Link>

        <form onSubmit={handleRegister} noValidate>
          <h1 className="text-lg font-sans font-semibold text-forest mb-6">Create your account</h1>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">
                  First name
                </label>
                <input
                  type="text"
                  autoComplete="given-name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150"
                />
              </div>
              <div>
                <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">
                  Last name
                </label>
                <input
                  type="text"
                  autoComplete="family-name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">
                Email
              </label>
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150"
                required
              />
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">
                Password
              </label>
              <input
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 12 characters"
                className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150"
                required
              />
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">
                Confirm password
              </label>
              <input
                type="password"
                autoComplete="new-password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="••••••••••••"
                className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150"
                required
              />
            </div>
          </div>

          {error && (
            <p className="mt-3 text-xs text-red-600 font-sans">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-6 w-full bg-forest text-mist text-sm font-sans font-medium py-3 rounded hover:bg-meadow transition-colors duration-150 disabled:opacity-50"
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>

          <div className="mt-5 text-center text-xs font-sans text-soil">
            Already have an account?{' '}
            <a href="/login" className="text-forest hover:underline underline-offset-2">
              Sign in
            </a>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function RegisterPage() {
  return (
    <Suspense fallback={null}>
      <RegisterForm />
    </Suspense>
  )
}
