import { apiClient } from './client'
import type {
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
  const { data } = await apiClient.post<Payout>(`/payments/admin/payouts/`)
  return data
}

export async function getSupplierPayouts(page = 1): Promise<PaginatedResponse<Payout>> {
  const { data } = await apiClient.get<PaginatedResponse<Payout>>('/payments/payouts/', { params: { page } })
  return data
}
