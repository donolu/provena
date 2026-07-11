'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { login, loginTotp } from '@/lib/api/auth'
import { mergeGuestCart } from '@/lib/api/cart'
import { safeNext } from '@/lib/navigation'
import { useAuthStore } from '@/store/auth'
import type { LoginResponse, TOTPLoginRequired } from '@/lib/api/types'

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login: storeLogin } = useAuthStore()

  const [email, setEmail]     = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)

  // TOTP step
  const [totpStep, setTotpStep]       = useState(false)
  const [totpToken, setTotpToken]     = useState('')
  const [totpCode, setTotpCode]       = useState('')
  const [totpError, setTotpError]     = useState('')
  const [totpLoading, setTotpLoading] = useState(false)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const result = await login(email, password)
      if ('totp_session_token' in result) {
        setTotpToken((result as TOTPLoginRequired).totp_session_token)
        setTotpStep(true)
      } else {
        const { access, user } = result as LoginResponse
        await mergeGuestCart(access).catch(() => {})
        storeLogin(user, access)
        const fallback = user.role === 'ADMIN' ? '/admin/dashboard' : user.role === 'SUPPLIER' ? '/supplier/dashboard' : '/catalogue'
        router.push(safeNext(searchParams.get('next'), fallback))
      }
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { error?: { message?: string }; detail?: string } } }).response?.data
      const msg = data?.error?.message ?? data?.detail ?? 'Invalid email or password.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  async function handleTotp(e: React.FormEvent) {
    e.preventDefault()
    setTotpError('')
    setTotpLoading(true)

    try {
      const { access, user } = await loginTotp(totpToken, totpCode)
      await mergeGuestCart(access).catch(() => {})
      storeLogin(user, access)
      const fallback = user.role === 'ADMIN' ? '/admin/dashboard' : user.role === 'SUPPLIER' ? '/supplier/dashboard' : '/catalogue'
      router.push(safeNext(searchParams.get('next'), fallback))
    } catch {
      setTotpError('Invalid code. Please try again.')
    } finally {
      setTotpLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-mist flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <Link href="/catalogue" className="block font-display italic text-2xl text-forest text-center mb-10">
          Provena
        </Link>

        {totpStep ? (
          <form onSubmit={handleTotp} noValidate>
            <h1 className="text-lg font-sans font-semibold text-forest mb-1">Two-step verification</h1>
            <p className="text-sm text-soil mb-6">Enter the code from your authenticator app.</p>

            <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">
              Authentication code
            </label>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
              placeholder="000000"
              className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-mono text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150 text-center tracking-[0.3em]"
            />

            {totpError && (
              <p className="mt-2 text-xs text-red-600 font-sans">{totpError}</p>
            )}

            <button
              type="submit"
              disabled={totpLoading || totpCode.length < 6}
              className="mt-5 w-full bg-forest text-mist text-sm font-sans font-medium py-3 rounded hover:bg-meadow transition-colors duration-150 disabled:opacity-50"
            >
              {totpLoading ? 'Verifying…' : 'Verify'}
            </button>

            <button
              type="button"
              onClick={() => setTotpStep(false)}
              className="mt-3 w-full text-xs text-soil hover:text-forest font-sans transition-colors duration-150"
            >
              Back to login
            </button>
          </form>
        ) : (
          <form onSubmit={handleLogin} noValidate>
            <h1 className="text-lg font-sans font-semibold text-forest mb-6">Sign in</h1>

            <div className="space-y-4">
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
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
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
              {loading ? 'Signing in…' : 'Sign in'}
            </button>

            <div className="mt-5 flex items-center justify-between text-xs font-sans text-soil">
              <a href="/register" className="hover:text-forest transition-colors duration-150">
                Create account
              </a>
              <a href="/reset-password" className="hover:text-forest transition-colors duration-150">
                Forgot password?
              </a>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  )
}
