import { apiClient } from './client'
import type {
  AdminUser,
  PaginatedResponse,
  Payout,
  RevenueDataPoint,
  SalesSummary,
  SupplierPerformanceStat,
  TopProduct,
} from './types'

// ── Analytics ─────────────────────────────────────────────────────────────────

export async function getSalesSummary(params?: {
  days?: number
}): Promise<SalesSummary> {
  const { data } = await apiClient.get<SalesSummary>('/analytics/sales/summary/', { params })
  return data
}

export async function getRevenueOverTime(params?: {
  days?: number
}): Promise<RevenueDataPoint[]> {
  const { data } = await apiClient.get<RevenueDataPoint[]>('/analytics/sales/over-time/', {
    params,
  })
  return data
}

export async function getTopProducts(params?: {
  limit?: number
}): Promise<TopProduct[]> {
  const { data } = await apiClient.get<TopProduct[]>('/analytics/products/top/', { params })
  return data
}

export async function getSupplierPerformance(): Promise<SupplierPerformanceStat[]> {
  const { data } = await apiClient.get<SupplierPerformanceStat[]>('/analytics/suppliers/')
  return data
}

// ── Payouts ───────────────────────────────────────────────────────────────────

export async function getAdminPayouts(params?: {
  status?: string
  page?: number
}): Promise<PaginatedResponse<Payout>> {
  const { data } = await apiClient.get<PaginatedResponse<Payout>>('/payments/admin/payouts/', { params })
  return data
}

export async function processAdminPayout(payoutId: string): Promise<Payout> {
  const { data } = await apiClient.post<Payout>(`/payments/admin/payouts/${payoutId}/process/`)
  return data
}

export async function getSupplierPayouts(page = 1): Promise<PaginatedResponse<Payout>> {
  const { data } = await apiClient.get<PaginatedResponse<Payout>>('/payments/payouts/', { params: { page } })
  return data
}

// ── Admin Users ───────────────────────────────────────────────────────────────

export async function getAdminUsers(params?: {
  role?: string
  q?: string
  page?: number
}): Promise<PaginatedResponse<AdminUser>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminUser>>('/auth/admin/users/', { params })
  return data
}

export async function suspendUser(userId: string): Promise<AdminUser> {
  const { data } = await apiClient.post<AdminUser>(`/auth/admin/users/${userId}/suspend/`)
  return data
}

export async function activateUser(userId: string): Promise<AdminUser> {
  const { data } = await apiClient.post<AdminUser>(`/auth/admin/users/${userId}/activate/`)
  return data
}

export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/auth/admin/users/${userId}/`)
}
