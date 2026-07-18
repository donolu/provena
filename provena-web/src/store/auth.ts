'use client'

import { create } from 'zustand'
import { configureAuth } from '@/lib/api/client'
import type { UserProfile } from '@/lib/api/types'

interface AuthState {
  user: UserProfile | null
  accessToken: string | null
  isInitialised: boolean
  login: (user: UserProfile, accessToken: string) => Promise<void>
  logout: () => Promise<void>
  setAccessToken: (token: string) => void
  setUser: (user: UserProfile) => Promise<void>
  initialise: () => Promise<void>
}

// Route-gating session cookies are set by the same-origin /session-sync route handler, which
// verifies the access token against Django and writes them httpOnly (so they cannot be forged
// client-side). Await these before navigating so the middleware sees the new/cleared session.
async function syncSessionCookies(accessToken: string) {
  try {
    await fetch('/session-sync', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    })
  } catch {
    // Advisory only — on failure the middleware falls back to gating to /login.
  }
}

async function clearSessionCookies() {
  try {
    await fetch('/session-sync', { method: 'DELETE' })
  } catch {
    // ignore
  }
}

export const useAuthStore = create<AuthState>((set, get) => {
  // Wire the API client to this store at creation time (no circular dep:
  // client.ts does not import from store/auth.ts).
  configureAuth(
    () => get().accessToken,
    () => {
      void get().logout()
    },
  )

  return {
    user: null,
    accessToken: null,
    isInitialised: false,

    async login(user, accessToken) {
      set({ user, accessToken })
      if (typeof window !== 'undefined') {
        await syncSessionCookies(accessToken)
      }
    },

    async logout() {
      set({ user: null, accessToken: null })
      if (typeof window !== 'undefined') {
        await clearSessionCookies()
      }
    },

    setAccessToken(token) {
      set({ accessToken: token })
    },

    async setUser(user) {
      set({ user })
      const token = get().accessToken
      if (typeof window !== 'undefined' && token) {
        await syncSessionCookies(token)
      }
    },

    async initialise() {
      if (typeof window === 'undefined') {
        set({ isInitialised: true })
        return
      }

      try {
        const axios = (await import('axios')).default
        const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
        // Refresh token is in the HttpOnly cookie — send no body, just credentials.
        const { data: tokens } = await axios.post(
          `${base}/api/v1/auth/refresh/`,
          {},
          { withCredentials: true },
        )

        const { apiClient } = await import('@/lib/api/client')
        const { data: profile } = await apiClient.get('/auth/me/', {
          headers: { Authorization: `Bearer ${tokens.access}` },
        })
        set({ user: profile, accessToken: tokens.access, isInitialised: true })
        await syncSessionCookies(tokens.access)
      } catch {
        await clearSessionCookies()
        set({ isInitialised: true })
      }
    },
  }
})
