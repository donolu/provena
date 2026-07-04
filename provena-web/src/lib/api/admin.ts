import { apiClient } from './client'
import type {
  AdminUser,
  AuditLog,
  Banner,
  PaginatedResponse,
  Payout,
  Product,
  RevenueDataPoint,
  Review,
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

// ── Admin Products ────────────────────────────────────────────────────────────

export async function getAdminProducts(params?: {
  status?: string
  supplier?: string
}): Promise<Product[]> {
  const { data } = await apiClient.get<Product[]>('/catalogue/admin/products/', { params })
  return data
}

export async function adminToggleFeature(slug: string): Promise<Product> {
  const { data } = await apiClient.post<Product>(`/catalogue/admin/products/${slug}/feature/`)
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

// ── Admin Reviews ─────────────────────────────────────────────────────────────

export async function getAdminReviews(params?: {
  is_approved?: boolean
}): Promise<Review[]> {
  const { data } = await apiClient.get<Review[]>('/marketplace/admin/reviews/', { params })
  return data
}

export async function adminApproveReview(id: string): Promise<Review> {
  const { data } = await apiClient.post<Review>(`/marketplace/admin/reviews/${id}/approve/`)
  return data
}

export async function adminDeleteReview(id: string): Promise<void> {
  await apiClient.delete(`/marketplace/admin/reviews/${id}/`)
}

export async function getAuditLog(params?: { action?: string; page?: number }): Promise<PaginatedResponse<AuditLog>> {
  const { data } = await apiClient.get<PaginatedResponse<AuditLog>>('/auth/admin/audit-log/', { params })
  return data
}

export async function getBanners(): Promise<PaginatedResponse<Banner>> {
  const { data } = await apiClient.get<PaginatedResponse<Banner>>('/catalogue/admin/banners/')
  return data
}

export async function createBanner(payload: Omit<Banner, 'id' | 'created_at' | 'updated_at'>): Promise<Banner> {
  const { data } = await apiClient.post<Banner>('/catalogue/admin/banners/', payload)
  return data
}

export async function updateBanner(id: string, payload: Partial<Omit<Banner, 'id' | 'created_at' | 'updated_at'>>): Promise<Banner> {
  const { data } = await apiClient.patch<Banner>(`/catalogue/admin/banners/${id}/`, payload)
  return data
}

export async function deleteBanner(id: string): Promise<void> {
  await apiClient.delete(`/catalogue/admin/banners/${id}/`)
}
