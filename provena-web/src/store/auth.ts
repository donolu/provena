'use client'

import { create } from 'zustand'
import { configureAuth } from '@/lib/api/client'
import type { UserProfile } from '@/lib/api/types'

interface AuthState {
  user: UserProfile | null
  accessToken: string | null
  isInitialised: boolean
  login: (user: UserProfile, accessToken: string) => void
  logout: () => void
  setAccessToken: (token: string) => void
  setUser: (user: UserProfile) => void
  initialise: () => Promise<void>
}

function setSessionCookies(user: UserProfile) {
  document.cookie = `has_session=1; path=/; SameSite=Lax`
  document.cookie = `user_role=${user.role}; path=/; SameSite=Lax`
  document.cookie = `totp_enabled=${user.totp_enabled ? '1' : '0'}; path=/; SameSite=Lax`
}

function clearSessionCookies() {
  document.cookie = 'has_session=; path=/; max-age=0'
  document.cookie = 'user_role=; path=/; max-age=0'
  document.cookie = 'totp_enabled=; path=/; max-age=0'
}

export const useAuthStore = create<AuthState>((set, get) => {
  // Wire the API client to this store at creation time (no circular dep:
  // client.ts does not import from store/auth.ts).
  configureAuth(
    () => get().accessToken,
    () => get().logout(),
  )

  return {
    user: null,
    accessToken: null,
    isInitialised: false,

    login(user, accessToken) {
      if (typeof window !== 'undefined') {
        setSessionCookies(user)
      }
      set({ user, accessToken })
    },

    logout() {
      if (typeof window !== 'undefined') {
        clearSessionCookies()
      }
      set({ user: null, accessToken: null })
    },

    setAccessToken(token) {
      set({ accessToken: token })
    },

    setUser(user) {
      if (typeof window !== 'undefined') {
        setSessionCookies(user)
      }
      set({ user })
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
        setSessionCookies(profile)
        set({ user: profile, accessToken: tokens.access, isInitialised: true })
      } catch {
        clearSessionCookies()
        set({ isInitialised: true })
      }
    },
  }
})
