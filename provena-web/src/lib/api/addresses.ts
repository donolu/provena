import { apiClient } from './client'

export interface Address {
  id: string
  label: string
  full_name: string
  line1: string
  line2: string
  city: string
  postcode: string
  country: string
  is_default: boolean
  created_at: string
  updated_at: string
}

export type AddressPayload = Omit<Address, 'id' | 'is_default' | 'created_at' | 'updated_at'> & {
  is_default?: boolean
}

export async function getAddresses(): Promise<Address[]> {
  const { data } = await apiClient.get<Address[]>('/auth/addresses/')
  return data
}

export async function createAddress(payload: AddressPayload): Promise<Address> {
  const { data } = await apiClient.post<Address>('/auth/addresses/', payload)
  return data
}

export async function updateAddress(id: string, payload: Partial<AddressPayload>): Promise<Address> {
  const { data } = await apiClient.patch<Address>(`/auth/addresses/${id}/`, payload)
  return data
}

export async function deleteAddress(id: string): Promise<void> {
  await apiClient.delete(`/auth/addresses/${id}/`)
}

export async function setDefaultAddress(id: string): Promise<Address> {
  const { data } = await apiClient.post<Address>(`/auth/addresses/${id}/default/`)
  return data
}
