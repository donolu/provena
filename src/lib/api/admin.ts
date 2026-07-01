import { apiClient } from './client'
import type {
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
}): Promise<Payout[]> {
  const { data } = await apiClient.get<Payout[]>('/payments/admin/payouts/', { params })
  return data
}

export async function processAdminPayout(payoutId: string): Promise<Payout> {
  const { data } = await apiClient.post<Payout>(`/payments/admin/payouts/`)
  return data
}

export async function getSupplierPayouts(): Promise<Payout[]> {
  const { data } = await apiClient.get<Payout[]>('/payments/payouts/')
  return data
}
