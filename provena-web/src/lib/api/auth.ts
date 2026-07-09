import { apiClient } from './client'
import type { LoginResponse, TOTPLoginRequired, UserProfile } from './types'

export async function login(email: string, password: string) {
  const { data } = await apiClient.post<LoginResponse | TOTPLoginRequired>(
    '/auth/login/',
    { email, password },
    { withCredentials: true },
  )
  return data
}

export async function loginTotp(totpSessionToken: string, totpCode: string) {
  const { data } = await apiClient.post<LoginResponse>(
    '/auth/login/totp/',
    { totp_session_token: totpSessionToken, totp_code: totpCode },
    { withCredentials: true },
  )
  return data
}

export async function logout() {
  await apiClient.post('/auth/logout/', {}, { withCredentials: true })
}

export async function getMe() {
  const { data } = await apiClient.get<UserProfile>('/auth/me/')
  return data
}

export async function updateMe(payload: { first_name?: string; last_name?: string }) {
  const { data } = await apiClient.patch<UserProfile>('/auth/me/', payload)
  return data
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
  newPasswordConfirm: string,
) {
  await apiClient.post('/auth/change-password/', {
    current_password: currentPassword,
    new_password: newPassword,
    new_password_confirm: newPasswordConfirm,
  })
}

export async function register(payload: {
  email: string
  password: string
  password_confirm: string
  first_name?: string
  last_name?: string
}) {
  const { data } = await apiClient.post<LoginResponse>('/auth/register/', payload, {
    withCredentials: true,
  })
  return data
}

export async function requestPasswordReset(email: string) {
  await apiClient.post('/auth/password-reset/', { email })
}

export async function confirmPasswordReset(
  token: string,
  newPassword: string,
  newPasswordConfirm: string,
) {
  await apiClient.post('/auth/password-reset/confirm/', {
    token,
    new_password: newPassword,
    new_password_confirm: newPasswordConfirm,
  })
}

export async function getTotpSetupUri(): Promise<{ otpauth_uri: string }> {
  const { data } = await apiClient.get<{ otpauth_uri: string }>('/auth/totp/setup/')
  return data
}

export async function enableTotp(code: string): Promise<void> {
  await apiClient.post('/auth/totp/enable/', { code })
}

export async function disableTotp(code: string): Promise<void> {
  await apiClient.post('/auth/totp/disable/', { code })
}
