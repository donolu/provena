import axios from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Auth helper slots — set once by useAuthStore on store creation
let _getToken: () => string | null = () => null
let _onLogout: () => void = () => {}

export function configureAuth(getToken: () => string | null, onLogout: () => void) {
  _getToken = getToken
  _onLogout = onLogout
}

// ── Request interceptor: attach Bearer token ──────────────────────────────────
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = _getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor: refresh on 401 ─────────────────────────────────────
let _refreshing = false
let _queue: Array<{ resolve: (t: string) => void; reject: (e: unknown) => void }> = []

function drainQueue(err: unknown, token: string | null) {
  _queue.forEach(({ resolve, reject }) => (err ? reject(err) : resolve(token!)))
  _queue = []
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    const isAuthEndpoint = original.url?.startsWith('/auth/login') || original.url?.startsWith('/auth/totp')
    if (error.response?.status !== 401 || original._retry || isAuthEndpoint) {
      return Promise.reject(error)
    }

    if (_refreshing) {
      return new Promise<string>((resolve, reject) => {
        _queue.push({ resolve, reject })
      }).then((token) => {
        original.headers.Authorization = `Bearer ${token}`
        return apiClient(original)
      })
    }

    original._retry = true
    _refreshing = true

    const storedRefresh =
      typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null

    if (!storedRefresh) {
      _onLogout()
      _refreshing = false
      return Promise.reject(error)
    }

    try {
      const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh/`, {
        refresh: storedRefresh,
      })
      const newAccess: string = data.access
      localStorage.setItem('refresh_token', data.refresh)
      // Push new access token into the store without importing the store here
      _onLogout = _onLogout  // keep logout reference
      // Notify store via a custom event so it can update accessToken
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('provena:token-refreshed', { detail: newAccess }))
      }
      drainQueue(null, newAccess)
      original.headers.Authorization = `Bearer ${newAccess}`
      return apiClient(original)
    } catch (err) {
      drainQueue(err, null)
      _onLogout()
      return Promise.reject(err)
    } finally {
      _refreshing = false
    }
  },
)
