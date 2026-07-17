import { type NextRequest, NextResponse } from 'next/server'

// Same-origin session cookies for middleware route-gating. Unlike client-written cookies,
// these are httpOnly (the browser JS cannot forge them) and their role is taken from the
// server — POST verifies the caller's access token against Django /auth/me and sets the
// cookies from the *verified* profile, so a user cannot grant themselves a role they lack.
// Being same-origin, they reach the Next middleware in both dev (cross-origin API) and prod
// (single nginx origin), which a cookie set by Django directly would not in dev.

const NAMES = ['has_session', 'user_role', 'totp_enabled'] as const

function apiBase(): string {
  return (
    process.env.API_URL_INTERNAL ??
    process.env.NEXT_PUBLIC_API_URL ??
    'http://localhost:8000'
  )
}

function clearOn(res: NextResponse): NextResponse {
  for (const name of NAMES) res.cookies.set(name, '', { path: '/', maxAge: 0 })
  return res
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const token = req.headers.get('authorization')?.replace(/^Bearer\s+/i, '')
  if (!token) {
    return clearOn(NextResponse.json({ ok: false }, { status: 401 }))
  }

  let profile: { role?: string; totp_enabled?: boolean }
  try {
    const meRes = await fetch(`${apiBase()}/api/v1/auth/me/`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
    if (!meRes.ok) {
      return clearOn(NextResponse.json({ ok: false }, { status: 401 }))
    }
    profile = await meRes.json()
  } catch {
    // Cannot reach the API to verify — do not set a session; middleware will gate to login.
    return clearOn(NextResponse.json({ ok: false }, { status: 502 }))
  }

  const res = NextResponse.json({ ok: true })
  const opts = {
    httpOnly: true,
    sameSite: 'lax' as const,
    path: '/',
    secure: process.env.NODE_ENV === 'production',
  }
  res.cookies.set('has_session', '1', opts)
  res.cookies.set('user_role', profile.role ?? '', opts)
  res.cookies.set('totp_enabled', profile.totp_enabled ? '1' : '0', opts)
  return res
}

export async function DELETE(): Promise<NextResponse> {
  return clearOn(NextResponse.json({ ok: true }))
}
