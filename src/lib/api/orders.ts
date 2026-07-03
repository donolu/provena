import { apiClient } from './client'
import type { Order, PaginatedResponse, SubOrderListItem } from './types'

export interface PaymentIntentResponse {
  client_secret: string
  payment_id: string
  amount: string
}

export async function createPaymentIntent(
  orderReference: string,
): Promise<PaymentIntentResponse> {
  const { data } = await apiClient.post<PaymentIntentResponse>('/payments/create-intent/', {
    order_reference: orderReference,
  })
  return data
}

// ── Buyer ─────────────────────────────────────────────────────────────────────

export async function getOrders(page = 1): Promise<PaginatedResponse<Order>> {
  const { data } = await apiClient.get<PaginatedResponse<Order>>('/orders/', { params: { page } })
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

export async function getSupplierSubOrders(page = 1): Promise<PaginatedResponse<SubOrderListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<SubOrderListItem>>('/orders/supplier/', { params: { page } })
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

export async function getAdminOrders(page = 1): Promise<PaginatedResponse<Order>> {
  const { data } = await apiClient.get<PaginatedResponse<Order>>('/orders/admin/', { params: { page } })
  return data
}

export async function getAdminOrder(reference: string): Promise<Order> {
  const { data } = await apiClient.get<Order>(`/orders/admin/${reference}/`)
  return data
}

export async function adminRefundPayment(paymentId: string, amount?: number): Promise<void> {
  await apiClient.post(`/payments/admin/payments/${paymentId}/refund/`, {
    ...(amount !== undefined && { amount }),
  })
}
