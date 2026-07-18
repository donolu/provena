import { type NextRequest, NextResponse } from 'next/server'

// Same-origin session cookies for middleware route-gating. Unlike client-written cookies,
// these are httpOnly (the browser JS cannot forge them) and their role is taken from the
// server — POST verifies the caller's access token against Django /auth/me and sets the
// cookies from the *verified* profile, so a user cannot grant themselves a role they lack.
// Being same-origin, they reach the Next middleware in both dev (cross-origin API) and prod
// (single nginx origin), which a cookie set by Django directly would not in dev.
//
// NOTE: this route lives OUTSIDE /api/* on purpose — the single-origin nginx proxies /api/*
// to Django, so a route under /api/ would never reach the Next server. Server-side calls use
// API_URL_INTERNAL (the internal API address), since inside a container the browser-facing
// origin (localhost / nginx) is not the API.

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

  // Mark Secure only when actually served over HTTPS — deriving from NODE_ENV would set Secure
  // on a production build served over plain HTTP (e.g. the E2E stack), which the browser drops.
  const proto = req.headers.get('x-forwarded-proto') ?? req.nextUrl.protocol.replace(':', '')
  const res = NextResponse.json({ ok: true })
  const opts = {
    httpOnly: true,
    sameSite: 'lax' as const,
    path: '/',
    secure: proto === 'https',
  }
  res.cookies.set('has_session', '1', opts)
  res.cookies.set('user_role', profile.role ?? '', opts)
  res.cookies.set('totp_enabled', profile.totp_enabled ? '1' : '0', opts)
  return res
}

export async function DELETE(): Promise<NextResponse> {
  return clearOn(NextResponse.json({ ok: true }))
}
