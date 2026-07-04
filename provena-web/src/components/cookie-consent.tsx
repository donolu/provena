'use client'

import { useState } from 'react'
import Link from 'next/link'

const COOKIE_KEY = 'cookie_consent'

function hasConsentCookie(): boolean {
  if (typeof document === 'undefined') return true
  return document.cookie.split(';').some((c) => c.trim().startsWith(`${COOKIE_KEY}=`))
}

export function CookieConsent() {
  const [visible, setVisible] = useState(() => !hasConsentCookie())

  function accept() {
    const expires = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toUTCString()
    document.cookie = `${COOKIE_KEY}=accepted; path=/; expires=${expires}; SameSite=Lax`
    setVisible(false)
  }

  function decline() {
    const expires = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toUTCString()
    document.cookie = `${COOKIE_KEY}=declined; path=/; expires=${expires}; SameSite=Lax`
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      className="fixed bottom-0 inset-x-0 z-50 p-4 sm:p-6 pointer-events-none"
    >
      <div className="max-w-2xl mx-auto bg-forest text-white rounded-xl shadow-2xl p-5 pointer-events-auto">
        <p className="text-sm font-sans text-white/90 leading-relaxed">
          We use cookies to improve your experience and for analytics. By clicking{' '}
          <strong className="text-white">Accept all</strong>, you consent to our use of cookies in
          accordance with our{' '}
          <Link href="/privacy" className="underline underline-offset-2 hover:text-marigold transition-colors">
            Privacy policy
          </Link>
          . Required cookies are always active.
        </p>
        <div className="flex items-center gap-3 mt-4">
          <button
            onClick={accept}
            className="px-4 py-2 bg-marigold text-forest text-sm font-sans font-medium rounded-lg hover:bg-marigold/90 transition-colors"
          >
            Accept all
          </button>
          <button
            onClick={decline}
            className="px-4 py-2 bg-white/10 text-white text-sm font-sans rounded-lg hover:bg-white/20 transition-colors"
          >
            Decline optional cookies
          </button>
        </div>
      </div>
    </div>
  )
}
