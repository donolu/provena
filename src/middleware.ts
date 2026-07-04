import { type NextRequest, NextResponse } from 'next/server'

// Routes that are only accessible when NOT logged in
const AUTH_ONLY_PATHS = ['/login', '/register']

// Routes requiring authentication — matched as prefix so /orders/REF-001 is covered
const PROTECTED_PREFIXES = [
  '/orders',
  '/checkout',
  '/wishlist',
  '/account',
]

// Routes requiring the SUPPLIER role
const SUPPLIER_PREFIXES = ['/supplier']

// Routes requiring the ADMIN role
const ADMIN_PREFIXES = ['/admin']

function getCookie(req: NextRequest, name: string): string | undefined {
  return req.cookies.get(name)?.value
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  const hasSession = getCookie(req, 'has_session') === '1'
  const role = getCookie(req, 'user_role') // 'BUYER' | 'SUPPLIER' | 'ADMIN' | undefined
  const totpEnabled = getCookie(req, 'totp_enabled') === '1'

  // Redirect logged-in users away from login/register
  if (hasSession && AUTH_ONLY_PATHS.some((p) => pathname.startsWith(p))) {
    const dest = role === 'ADMIN' ? '/admin/dashboard'
      : role === 'SUPPLIER' ? '/supplier/dashboard'
      : '/catalogue'
    return NextResponse.redirect(new URL(dest, req.url))
  }

  // Admin routes — require ADMIN role
  if (ADMIN_PREFIXES.some((p) => pathname.startsWith(p))) {
    if (!hasSession) {
      const url = req.nextUrl.clone()
      url.pathname = '/login'
      url.searchParams.set('next', pathname)
      return NextResponse.redirect(url)
    }
    if (role !== 'ADMIN') {
      return NextResponse.redirect(new URL('/catalogue', req.url))
    }
    // Enforce TOTP setup before accessing admin area
    if (!totpEnabled && pathname !== '/account/security') {
      return NextResponse.redirect(new URL('/account/security?enforce=1', req.url))
    }
    return NextResponse.next()
  }

  // Supplier routes — require SUPPLIER role
  if (SUPPLIER_PREFIXES.some((p) => pathname.startsWith(p))) {
    if (!hasSession) {
      const url = req.nextUrl.clone()
      url.pathname = '/login'
      url.searchParams.set('next', pathname)
      return NextResponse.redirect(url)
    }
    if (role !== 'SUPPLIER') {
      return NextResponse.redirect(new URL('/catalogue', req.url))
    }
    // Enforce TOTP setup before accessing supplier area
    if (!totpEnabled && pathname !== '/account/security') {
      return NextResponse.redirect(new URL('/account/security?enforce=1', req.url))
    }
    return NextResponse.next()
  }

  // Buyer-facing protected routes — require any authenticated session
  if (PROTECTED_PREFIXES.some((p) => pathname.startsWith(p))) {
    if (!hasSession) {
      const url = req.nextUrl.clone()
      url.pathname = '/login'
      url.searchParams.set('next', pathname)
      return NextResponse.redirect(url)
    }
    return NextResponse.next()
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/login',
    '/register',
    '/orders/:path*',
    '/checkout/:path*',
    '/wishlist/:path*',
    '/account/:path*',
    '/supplier/:path*',
    '/admin/:path*',
  ],
}
