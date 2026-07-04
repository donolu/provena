'use client'

import { useAuthGuard } from '@/hooks/use-auth-guard'
import type { UserRole } from '@/lib/api/types'

/**
 * Thin client wrapper that enforces auth for a layout.
 * Place inside a layout.tsx to protect all child routes.
 */
export function AuthGuard({
  children,
  requiredRole,
}: {
  children: React.ReactNode
  requiredRole?: UserRole
}) {
  useAuthGuard(requiredRole)
  return <>{children}</>
}
