'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/store/auth'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { initialise, setAccessToken } = useAuthStore()

  useEffect(() => {
    initialise()

    // Update access token when the API client refreshes it
    function onTokenRefreshed(e: Event) {
      const token = (e as CustomEvent<string>).detail
      setAccessToken(token)
    }
    window.addEventListener('provena:token-refreshed', onTokenRefreshed)
    return () => window.removeEventListener('provena:token-refreshed', onTokenRefreshed)
  }, [initialise, setAccessToken])

  return <>{children}</>
}
