'use client'

import { Suspense, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { ShieldCheck, ShieldOff, KeyRound, AlertTriangle, Trash2 } from 'lucide-react'
import { getTotpSetupUri, enableTotp, disableTotp, getMe, deleteAccount } from '@/lib/api/auth'
import { useAuthStore } from '@/store/auth'

function extractSecret(otpauthUri: string): string {
  try {
    const url = new URL(otpauthUri)
    return url.searchParams.get('secret') ?? ''
  } catch {
    return ''
  }
}

function SecurityContent() {
  const searchParams = useSearchParams()
  const enforce = searchParams.get('enforce') === '1'

  const router = useRouter()
  const { user, setUser, logout } = useAuthStore()
  const [setupUri, setSetupUri] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [error, setError] = useState('')

  const [showDelete, setShowDelete] = useState(false)
  const [delPassword, setDelPassword] = useState('')
  const [delCode, setDelCode] = useState('')
  const [delError, setDelError] = useState('')

  const deleteMutation = useMutation({
    mutationFn: () => deleteAccount(delPassword, delCode),
    onSuccess: () => {
      logout()
      router.push('/')
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: { detail?: string } } }).response?.data
      setDelError(data?.detail ?? 'Could not delete your account. Please try again.')
    },
  })

  const setupMutation = useMutation({
    mutationFn: getTotpSetupUri,
    onSuccess: (data) => setSetupUri(data.otpauth_uri),
  })

  const enableMutation = useMutation({
    mutationFn: () => enableTotp(code),
    onSuccess: async () => {
      const profile = await getMe()
      setUser(profile)
      setSetupUri(null)
      setCode('')
      setError('')
    },
    onError: () => setError('Invalid code. Please try again.'),
  })

  const disableMutation = useMutation({
    mutationFn: () => disableTotp(code),
    onSuccess: async () => {
      const profile = await getMe()
      setUser(profile)
      setCode('')
      setError('')
    },
    onError: () => setError('Invalid code. Please try again.'),
  })

  const totpEnabled = user?.totp_enabled ?? false
  const secret = setupUri ? extractSecret(setupUri) : ''

  return (
    <div className="max-w-xl mx-auto px-6 py-10">
      <div className="flex items-center gap-3 mb-8">
        <KeyRound className="h-5 w-5 text-marigold" />
        <h1 className="font-display italic text-2xl text-forest">Security</h1>
      </div>

      {enforce && !totpEnabled && (
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
          <p className="text-sm font-sans text-amber-800">
            Your account role requires two-factor authentication before you can access that area.
            Set up an authenticator app below to continue.
          </p>
        </div>
      )}

      <div className="bg-white border border-stone-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-sans font-semibold text-forest text-sm">Authenticator app (TOTP)</h2>
          {totpEnabled ? (
            <span className="inline-flex items-center gap-1 text-xs font-sans font-medium text-green-700 bg-green-50 border border-green-200 rounded-full px-2.5 py-0.5">
              <ShieldCheck className="h-3 w-3" /> Enabled
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs font-sans font-medium text-stone-500 bg-stone-100 rounded-full px-2.5 py-0.5">
              <ShieldOff className="h-3 w-3" /> Not set up
            </span>
          )}
        </div>
        <p className="text-xs font-sans text-soil mb-5">
          Use Google Authenticator, Authy, or any TOTP-compatible app.
        </p>

        {!totpEnabled && !setupUri && (
          <button
            onClick={() => setupMutation.mutate()}
            disabled={setupMutation.isPending}
            className="px-4 py-2 bg-forest text-white text-sm font-sans rounded-lg hover:bg-forest/90 disabled:opacity-60 transition-colors"
          >
            {setupMutation.isPending ? 'Loading…' : 'Set up authenticator app'}
          </button>
        )}

        {!totpEnabled && setupUri && (
          <div className="space-y-4">
            <div>
              <p className="text-xs font-sans text-soil mb-2">
                1. Open your authenticator app and add a new account.
              </p>
              <p className="text-xs font-sans text-soil mb-2">
                2. Tap <strong>Enter a setup key</strong> and paste the key below, or tap{' '}
                <a
                  href={setupUri}
                  className="text-forest underline underline-offset-2"
                >
                  open in app
                </a>{' '}
                on a mobile device.
              </p>
              <div className="bg-stone-50 border border-stone-200 rounded-lg p-3 font-mono text-xs text-forest break-all select-all">
                {secret}
              </div>
            </div>

            <div>
              <p className="text-xs font-sans text-soil mb-2">
                3. Enter the 6-digit code from your app to confirm setup.
              </p>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => { setCode(e.target.value.replace(/\D/g, '')); setError('') }}
                placeholder="000000"
                className="w-32 px-3 py-2 border border-stone-300 rounded-lg font-mono text-sm text-center focus:outline-none focus:ring-2 focus:ring-forest/30"
              />
              {error && <p className="mt-1 text-xs text-red-600 font-sans">{error}</p>}
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => enableMutation.mutate()}
                disabled={enableMutation.isPending || code.length < 6}
                className="px-4 py-2 bg-forest text-white text-sm font-sans rounded-lg hover:bg-forest/90 disabled:opacity-60 transition-colors"
              >
                {enableMutation.isPending ? 'Verifying…' : 'Enable two-factor authentication'}
              </button>
              <button
                onClick={() => { setSetupUri(null); setCode(''); setError('') }}
                className="text-sm font-sans text-soil hover:text-forest transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {totpEnabled && (
          <div className="space-y-3">
            <p className="text-xs font-sans text-soil">
              Enter a code from your authenticator app to disable two-factor authentication.
            </p>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => { setCode(e.target.value.replace(/\D/g, '')); setError('') }}
              placeholder="000000"
              className="w-32 px-3 py-2 border border-stone-300 rounded-lg font-mono text-sm text-center focus:outline-none focus:ring-2 focus:ring-red-300"
            />
            {error && <p className="mt-1 text-xs text-red-600 font-sans">{error}</p>}
            <button
              onClick={() => disableMutation.mutate()}
              disabled={disableMutation.isPending || code.length < 6}
              className="px-4 py-2 bg-red-600 text-white text-sm font-sans rounded-lg hover:bg-red-700 disabled:opacity-60 transition-colors"
            >
              {disableMutation.isPending ? 'Disabling…' : 'Disable two-factor authentication'}
            </button>
          </div>
        )}

        <div className="border-t border-stone-200 mt-8 pt-6">
          <div className="flex items-center gap-2 mb-1">
            <Trash2 size={16} className="text-red-600" />
            <h2 className="font-sans font-semibold text-forest text-sm">Delete account</h2>
          </div>
          <p className="text-xs font-sans text-soil mb-3 max-w-md">
            Permanently erase your personal data and close your account. Order and payment records are kept as required by law but stripped of your details. This cannot be undone.
          </p>
          {!showDelete ? (
            <button
              onClick={() => setShowDelete(true)}
              className="px-4 py-2 border border-red-300 text-red-700 text-sm font-sans rounded-lg hover:bg-red-50 transition-colors"
            >
              Delete my account
            </button>
          ) : (
            <div className="space-y-3 max-w-xs">
              <input
                type="password"
                autoComplete="current-password"
                value={delPassword}
                onChange={(e) => { setDelPassword(e.target.value); setDelError('') }}
                placeholder="Confirm your password"
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
              />
              {totpEnabled && (
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={delCode}
                  onChange={(e) => { setDelCode(e.target.value.replace(/\D/g, '')); setDelError('') }}
                  placeholder="2FA code"
                  className="w-32 px-3 py-2 border border-stone-300 rounded-lg font-mono text-sm text-center focus:outline-none focus:ring-2 focus:ring-red-300"
                />
              )}
              {delError && <p className="text-xs text-red-600 font-sans">{delError}</p>}
              <div className="flex gap-2">
                <button
                  onClick={() => deleteMutation.mutate()}
                  disabled={deleteMutation.isPending || !delPassword || (totpEnabled && delCode.length < 6)}
                  className="px-4 py-2 bg-red-600 text-white text-sm font-sans rounded-lg hover:bg-red-700 disabled:opacity-60 transition-colors"
                >
                  {deleteMutation.isPending ? 'Deleting…' : 'Permanently delete'}
                </button>
                <button
                  onClick={() => { setShowDelete(false); setDelPassword(''); setDelCode(''); setDelError('') }}
                  className="px-4 py-2 text-sm font-sans text-soil hover:text-forest transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function SecurityPage() {
  return (
    <Suspense fallback={null}>
      <SecurityContent />
    </Suspense>
  )
}
