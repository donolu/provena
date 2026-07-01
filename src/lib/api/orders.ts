import { apiClient } from './client'
import type { Order, SubOrderListItem } from './types'

// ── Buyer ─────────────────────────────────────────────────────────────────────

export async function getOrders(): Promise<Order[]> {
  const { data } = await apiClient.get<Order[]>('/orders/')
  return data
}

export async function getOrder(reference: string): Promise<Order> {
  const { data } = await apiClient.get<Order>(`/orders/${reference}/`)
  return data
}

export async function placeOrder(payload: {
  items: Array<{ variant_id: string; quantity: number }>
  shipping_name: string
  shipping_line1: string
  shipping_line2?: string
  shipping_city: string
  shipping_postcode: string
  shipping_country: string
  notes?: string
}): Promise<Order> {
  const { data } = await apiClient.post<Order>('/orders/', payload)
  return data
}

export async function cancelOrder(reference: string): Promise<Order> {
  const { data } = await apiClient.post<Order>(`/orders/${reference}/cancel/`)
  return data
}

// ── Supplier ──────────────────────────────────────────────────────────────────

export async function getSupplierSubOrders(): Promise<SubOrderListItem[]> {
  const { data } = await apiClient.get<SubOrderListItem[]>('/orders/supplier/')
  return data
}

export async function confirmSubOrder(subOrderId: string): Promise<SubOrderListItem> {
  const { data } = await apiClient.post<SubOrderListItem>(
    `/orders/supplier/${subOrderId}/confirm/`,
  )
  return data
}

export async function dispatchSubOrder(
  subOrderId: string,
  trackingNumber?: string,
): Promise<SubOrderListItem> {
  const { data } = await apiClient.post<SubOrderListItem>(
    `/orders/supplier/${subOrderId}/dispatch/`,
    { tracking_number: trackingNumber ?? '' },
  )
  return data
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function getAdminOrders(): Promise<Order[]> {
  const { data } = await apiClient.get<Order[]>('/orders/admin/')
  return data
}

export async function getAdminOrder(reference: string): Promise<Order> {
  const { data } = await apiClient.get<Order>(`/orders/admin/${reference}/`)
  return data
}
