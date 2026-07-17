import { apiClient } from './client'
import type { AdminSupplier, PaginatedResponse, PublicSupplier, SupplierProfile } from './types'

// ── Public supplier profile ───────────────────────────────────────────────────

export async function getPublicSuppliers(): Promise<PublicSupplier[]> {
  const { data } = await apiClient.get<PublicSupplier[]>('/suppliers/')
  return data
}

export async function getPublicSupplier(slug: string): Promise<PublicSupplier> {
  const { data } = await apiClient.get<PublicSupplier>(`/suppliers/${slug}/`)
  return data
}

// ── Become a supplier ─────────────────────────────────────────────────────────

export interface SupplierRegistrationPayload {
  business_name: string
  description?: string
  phone?: string
  website?: string
  logo_url?: string
  address?: {
    line1: string
    line2?: string
    city: string
    county?: string
    postcode: string
    country?: string
  }
}

/**
 * Register the authenticated buyer as a supplier. The backend upgrades the
 * user's role to SUPPLIER and creates a PENDING profile awaiting KYC review.
 */
export async function registerSupplier(
  payload: SupplierRegistrationPayload,
): Promise<SupplierProfile> {
  const { data } = await apiClient.post<SupplierProfile>('/suppliers/register/', payload)
  return data
}

// ── Supplier self-service ─────────────────────────────────────────────────────

export async function getMySupplierProfile(): Promise<SupplierProfile> {
  const { data } = await apiClient.get<SupplierProfile>('/suppliers/me/')
  return data
}

export async function updateMySupplierProfile(
  payload: Partial<
    Pick<
      SupplierProfile,
      | 'business_name'
      | 'description'
      | 'logo_url'
      | 'website'
      | 'phone'
      | 'shipping_policy'
      | 'shipping_flat_rate'
      | 'shipping_per_item_rate'
      | 'free_shipping_threshold'
      | 'vat_number'
    >
  >,
): Promise<SupplierProfile> {
  const { data } = await apiClient.patch<SupplierProfile>('/suppliers/me/', payload)
  return data
}

export interface SupplierPerformanceResponse {
  total_revenue: string
  total_orders: number
  average_fulfilment_days: number | null
  return_rate: number
  active_products: number
}

export async function getMyPerformance(): Promise<SupplierPerformanceResponse> {
  const { data } = await apiClient.get<SupplierPerformanceResponse>('/suppliers/me/performance/')
  return data
}

export async function getStripeConnectUrl(): Promise<string> {
  const { data } = await apiClient.get<{ onboarding_url: string }>('/suppliers/me/stripe-connect/')
  return data.onboarding_url
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function getAdminSuppliers(params?: {
  status?: string
  search?: string
  page?: number
}): Promise<PaginatedResponse<AdminSupplier>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminSupplier>>('/suppliers/admin/', { params })
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

export async function updateSupplierCommission(
  id: string,
  commissionRate: string,
): Promise<AdminSupplier> {
  const { data } = await apiClient.patch<AdminSupplier>(`/suppliers/admin/${id}/`, {
    commission_rate: commissionRate,
  })
  return data
}
