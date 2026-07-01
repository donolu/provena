import { apiClient } from './client'
import type { Category, Product } from './types'

export async function getCategories(): Promise<Category[]> {
  const { data } = await apiClient.get<Category[]>('/catalogue/categories/')
  return data
}

export async function getCategory(slug: string): Promise<Category> {
  const { data } = await apiClient.get<Category>(`/catalogue/categories/${slug}/`)
  return data
}

export async function getProducts(params?: {
  category?: string
  search?: string
  page?: number
  page_size?: number
}): Promise<Product[]> {
  const { data } = await apiClient.get<Product[]>('/catalogue/products/', {
    params: { page_size: 100, ...params },
  })
  return data
}

export async function getProduct(slug: string): Promise<Product> {
  const { data } = await apiClient.get<Product>(`/catalogue/products/${slug}/`)
  return data
}

export async function getMyProducts(): Promise<Product[]> {
  const { data } = await apiClient.get<Product[]>('/catalogue/products/me/')
  return data
}
