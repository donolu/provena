'use client'

import { create } from 'zustand'
import { configureAuth } from '@/lib/api/client'
import type { UserProfile } from '@/lib/api/types'

interface AuthState {
  user: UserProfile | null
  accessToken: string | null
  isInitialised: boolean
  login: (user: UserProfile, accessToken: string, refreshToken: string) => void
  logout: () => void
  setAccessToken: (token: string) => void
  initialise: () => Promise<void>
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

    login(user, accessToken, refreshToken) {
      if (typeof window !== 'undefined') {
        localStorage.setItem('refresh_token', refreshToken)
      }
      set({ user, accessToken })
    },

    logout() {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('refresh_token')
      }
      set({ user: null, accessToken: null })
    },

    setAccessToken(token) {
      set({ accessToken: token })
    },

    async initialise() {
      if (typeof window === 'undefined') {
        set({ isInitialised: true })
        return
      }

      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        set({ isInitialised: true })
        return
      }

      try {
        const axios = (await import('axios')).default
        const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
        const { data: tokens } = await axios.post(`${base}/api/v1/auth/refresh/`, {
          refresh: refreshToken,
        })
        localStorage.setItem('refresh_token', tokens.refresh)

        const { apiClient } = await import('@/lib/api/client')
        const { data: profile } = await apiClient.get('/auth/me/', {
          headers: { Authorization: `Bearer ${tokens.access}` },
        })
        set({ user: profile, accessToken: tokens.access, isInitialised: true })
      } catch {
        localStorage.removeItem('refresh_token')
        set({ isInitialised: true })
      }
    },
  }
})
