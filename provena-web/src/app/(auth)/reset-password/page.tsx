'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { requestPasswordReset, confirmPasswordReset } from '@/lib/api/auth'

function extractError(err: unknown, fallback: string): string {
  const data = (err as {
    response?: { data?: Record<string, unknown> & { error?: { message?: string }; detail?: string } }
  }).response?.data
  let msg = data?.error?.message ?? data?.detail
  if (!msg && data && typeof data === 'object') {
    const first = Object.values(data)[0]
    msg = Array.isArray(first) ? String(first[0]) : typeof first === 'string' ? first : undefined
  }
  return msg ?? fallback
}

function RequestForm() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await requestPasswordReset(email)
      setSent(true)
    } catch (err: unknown) {
      setError(extractError(err, 'Could not send the reset link. Please try again.'))
    } finally {
      setLoading(false)
    }
  }

  if (sent) {
    return (
      <div>
        <h1 className="text-lg font-sans font-semibold text-forest mb-2">Check your email</h1>
        <p className="text-sm text-soil mb-6">
          If an account exists for <span className="text-forest font-medium">{email}</span>, we have sent a link to reset your password. The link expires in one hour.
        </p>
        <Link
          href="/login"
          className="inline-block w-full text-center bg-forest text-mist text-sm font-sans font-medium py-3 rounded hover:bg-meadow transition-colors duration-150"
        >
          Back to sign in
        </Link>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h1 className="text-lg font-sans font-semibold text-forest mb-1">Reset your password</h1>
      <p className="text-sm text-soil mb-6">Enter your email and we will send you a reset link.</p>

      <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">Email</label>
      <input
        type="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        className="w-full border border-hoarfrost rounded px-3 py-2.5 text-sm font-sans text-forest bg-white focus:outline-none focus:border-forest transition-colors duration-150"
        required
      />

      {error && <p className="mt-3 text-xs text-red-600 font-sans">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="mt-6 w-full bg-forest text-mist text-sm font-sans font-medium py-3 rounded hover:bg-meadow transition-colors duration-150 disabled:opacity-50"
      >
        {loading ? 'Sending…' : 'Send reset link'}
      </button>

      <div className="mt-5 text-center text-xs font-sans text-soil">
        Remembered it?{' '}
        <a href="/login" className="text-forest hover:underline underline-offset-2">Sign in</a>
      </div>
    </form>
  )
}

function ConfirmForm({ token }: { token: string }) {
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
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
      await confirmPasswordReset(token, password, passwordConfirm)
      setDone(true)
      setTimeout(() => router.push('/login'), 1800)
    } catch (err: unknown) {
      setError(extractError(err, 'This reset link is invalid or has expired. Request a new one.'))
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <div>
        <h1 className="text-lg font-sans font-semibold text-forest mb-2">Password updated</h1>
        <p className="text-sm text-soil mb-6">You can now sign in with your new password. Redirecting…</p>
        <Link
          href="/login"
          className="inline-block w-full text-center bg-forest text-mist text-sm font-sans font-medium py-3 rounded hover:bg-meadow transition-colors duration-150"
        >
          Sign in
        </Link>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h1 className="text-lg font-sans font-semibold text-forest mb-1">Set a new password</h1>
      <p className="text-sm text-soil mb-6">Choose a password of at least 12 characters.</p>

      <div className="space-y-4">
        <div>
          <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">New password</label>
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
          <label className="block text-[11px] uppercase tracking-[0.12em] text-soil font-sans mb-1.5">Confirm password</label>
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

      {error && <p className="mt-3 text-xs text-red-600 font-sans">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="mt-6 w-full bg-forest text-mist text-sm font-sans font-medium py-3 rounded hover:bg-meadow transition-colors duration-150 disabled:opacity-50"
      >
        {loading ? 'Updating…' : 'Update password'}
      </button>

      <div className="mt-5 text-center text-xs font-sans text-soil">
        <a href="/login" className="text-forest hover:underline underline-offset-2">Back to sign in</a>
      </div>
    </form>
  )
}

function ResetPassword() {
  const token = useSearchParams().get('token')
  return (
    <div className="min-h-screen bg-mist flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <Link href="/catalogue" className="block font-display italic text-2xl text-forest text-center mb-10">
          Provena
        </Link>
        {token ? <ConfirmForm token={token} /> : <RequestForm />}
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPassword />
    </Suspense>
  )
}
