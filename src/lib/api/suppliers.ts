import { apiClient } from './client'
import type { AdminSupplier, PaginatedResponse, SupplierProfile } from './types'

// ── Supplier self-service ─────────────────────────────────────────────────────

export async function getMySupplierProfile(): Promise<SupplierProfile> {
  const { data } = await apiClient.get<SupplierProfile>('/suppliers/me/')
  return data
}

export async function updateMySupplierProfile(
  payload: Partial<Pick<SupplierProfile, 'business_name' | 'description' | 'logo_url' | 'website' | 'phone'>>,
): Promise<SupplierProfile> {
  const { data } = await apiClient.patch<SupplierProfile>('/suppliers/me/', payload)
  return data
}

export interface SupplierPerformanceResponse {
  total_revenue: string
  total_orders: number
  pending_orders: number
  avg_order_value: string
}

export async function getMyPerformance(): Promise<SupplierPerformanceResponse> {
  const { data } = await apiClient.get<SupplierPerformanceResponse>('/suppliers/me/performance/')
  return data
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function getAdminSuppliers(params?: {
  status?: string
  search?: string
  page?: number
}): Promise<PaginatedResponse<AdminSupplier>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminSupplier>>('/suppliers/admin/', {
    params,
  })
  return data
}

export async function getAdminSupplier(id: string): Promise<AdminSupplier> {
  const { data } = await apiClient.get<AdminSupplier>(`/suppliers/admin/${id}/`)
  return data
}

export async function approveSupplier(id: string, reason?: string): Promise<AdminSupplier> {
  const { data } = await apiClient.post<AdminSupplier>(`/suppliers/admin/${id}/approve/`, {
    reason: reason ?? '',
  })
  return data
}

export async function rejectSupplier(id: string, reason?: string): Promise<AdminSupplier> {
  const { data } = await apiClient.post<AdminSupplier>(`/suppliers/admin/${id}/reject/`, {
    reason: reason ?? '',
  })
  return data
}

export async function suspendSupplier(id: string, reason?: string): Promise<AdminSupplier> {
  const { data } = await apiClient.post<AdminSupplier>(`/suppliers/admin/${id}/suspend/`, {
    reason: reason ?? '',
  })
  return data
}
