import { apiClient } from './client'
import type { Order, OrderDispute, OrderReturn, PaginatedResponse, Payment, SubOrderListItem } from './types'

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

export async function getPayments(page = 1): Promise<PaginatedResponse<Payment>> {
  const { data } = await apiClient.get<PaginatedResponse<Payment>>('/payments/', { params: { page } })
  return data
}

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

export async function requestReturn(
  reference: string,
  subOrderId: string,
  reason: string,
): Promise<OrderReturn> {
  const { data } = await apiClient.post<OrderReturn>(
    `/orders/${reference}/sub-orders/${subOrderId}/return/`,
    { reason },
  )
  return data
}

export async function getSupplierReturns(
  returnStatus?: string,
  page = 1,
): Promise<PaginatedResponse<OrderReturn>> {
  const { data } = await apiClient.get<PaginatedResponse<OrderReturn>>(
    '/orders/supplier/returns/',
    { params: { page, ...(returnStatus ? { status: returnStatus } : {}) } },
  )
  return data
}

export async function supplierApproveReturn(id: string, notes?: string): Promise<OrderReturn> {
  const { data } = await apiClient.post<OrderReturn>(
    `/orders/supplier/returns/${id}/approve/`,
    { notes: notes ?? '' },
  )
  return data
}

export async function supplierRejectReturn(id: string, notes?: string): Promise<OrderReturn> {
  const { data } = await apiClient.post<OrderReturn>(
    `/orders/supplier/returns/${id}/reject/`,
    { notes: notes ?? '' },
  )
  return data
}

export async function getAdminReturns(
  returnStatus?: string,
  page = 1,
): Promise<PaginatedResponse<OrderReturn>> {
  const { data } = await apiClient.get<PaginatedResponse<OrderReturn>>(
    '/orders/admin/returns/',
    { params: { page, ...(returnStatus ? { status: returnStatus } : {}) } },
  )
  return data
}

export async function adminProcessReturnRefund(
  id: string,
  amount?: number,
): Promise<OrderReturn> {
  const { data } = await apiClient.post<OrderReturn>(
    `/orders/admin/returns/${id}/refund/`,
    amount !== undefined ? { amount } : {},
  )
  return data
}

export async function raiseDispute(
  reference: string,
  subOrderId: string,
  reason: string,
): Promise<OrderDispute> {
  const { data } = await apiClient.post<OrderDispute>(
    `/orders/${reference}/sub-orders/${subOrderId}/dispute/`,
    { reason },
  )
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

export async function getAdminDisputes(disputeStatus?: string): Promise<OrderDispute[]> {
  const { data } = await apiClient.get<OrderDispute[]>('/orders/admin/disputes/', {
    params: disputeStatus ? { status: disputeStatus } : undefined,
  })
  return data
}

export async function adminResolveDispute(id: string, resolution: string): Promise<OrderDispute> {
  const { data } = await apiClient.post<OrderDispute>(`/orders/admin/disputes/${id}/resolve/`, {
    resolution,
  })
  return data
}

export async function adminRejectDispute(id: string, resolution: string): Promise<OrderDispute> {
  const { data } = await apiClient.post<OrderDispute>(`/orders/admin/disputes/${id}/reject/`, {
    resolution,
  })
  return data
}

export async function getWsTicket(): Promise<string> {
  const { data } = await apiClient.post<{ ticket: string }>('/orders/ws-ticket/')
  return data.ticket
}
