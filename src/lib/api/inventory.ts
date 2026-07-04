import { apiClient } from './client'
import type { StockLevel, StockLot, StockMovement } from './types'

const BASE = '/inventory'

export async function getInventory(lowStock?: boolean): Promise<StockLevel[]> {
  const { data } = await apiClient.get<StockLevel[]>(BASE + '/', {
    params: lowStock ? { low_stock: 'true' } : undefined,
  })
  return data
}

export async function getStockLevel(variantId: string): Promise<StockLevel> {
  const { data } = await apiClient.get<StockLevel>(`${BASE}/${variantId}/`)
  return data
}

export async function setThreshold(variantId: string, threshold: number): Promise<StockLevel> {
  const { data } = await apiClient.patch<StockLevel>(`${BASE}/${variantId}/`, {
    low_stock_threshold: threshold,
  })
  return data
}

export async function receiveStock(
  variantId: string,
  payload: { quantity: number; lot_number?: string; expires_at?: string | null; notes?: string },
): Promise<StockLevel> {
  const { data } = await apiClient.post<StockLevel>(`${BASE}/${variantId}/receive/`, payload)
  return data
}

export async function adjustStock(
  variantId: string,
  payload: { delta: number; notes: string },
): Promise<StockLevel> {
  const { data } = await apiClient.post<StockLevel>(`${BASE}/${variantId}/adjust/`, payload)
  return data
}

export async function getStockLots(variantId: string): Promise<StockLot[]> {
  const { data } = await apiClient.get<StockLot[]>(`${BASE}/${variantId}/lots/`)
  return data
}

export async function getStockMovements(variantId: string): Promise<StockMovement[]> {
  const { data } = await apiClient.get<StockMovement[]>(`${BASE}/${variantId}/movements/`)
  return data
}
