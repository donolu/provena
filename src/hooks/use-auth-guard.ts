'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/auth'
import type { UserRole } from '@/lib/api/types'

/**
 * Enforces that the current user is authenticated and (optionally) has the
 * required role. Redirects to /login if unauthenticated, or to /catalogue if
 * the role does not match. Only runs after the store has been initialised so
 * it does not redirect during the initial token-refresh window.
 */
export function useAuthGuard(requiredRole?: UserRole) {
  const router = useRouter()
  const user = useAuthStore((s) => s.user)
  const isInitialised = useAuthStore((s) => s.isInitialised)

  useEffect(() => {
    if (!isInitialised) return

    if (!user) {
      const next = encodeURIComponent(window.location.pathname)
      router.replace(`/login?next=${next}`)
      return
    }

    if (requiredRole && user.role !== requiredRole) {
      router.replace('/catalogue')
    }
  }, [isInitialised, user, requiredRole, router])
}
