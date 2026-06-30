import { apiClient } from './client'
import type { Cart, WishlistItem } from './types'

// ── Cart ──────────────────────────────────────────────────────────────────────

export async function getCart(): Promise<Cart> {
  const { data } = await apiClient.get<Cart>('/marketplace/cart/')
  return data
}

export async function addToCart(variantId: string, quantity: number): Promise<Cart> {
  const { data } = await apiClient.post<Cart>('/marketplace/cart/items/', {
    variant_id: variantId,
    quantity,
  })
  return data
}

export async function updateCartItem(itemId: string, quantity: number): Promise<Cart> {
  const { data } = await apiClient.patch<Cart>(`/marketplace/cart/items/${itemId}/`, { quantity })
  return data
}

export async function removeCartItem(itemId: string): Promise<void> {
  await apiClient.delete(`/marketplace/cart/items/${itemId}/`)
}

// ── Wishlist ──────────────────────────────────────────────────────────────────

export async function getWishlist(): Promise<WishlistItem[]> {
  const { data } = await apiClient.get<WishlistItem[]>('/marketplace/wishlist/')
  return data
}

export async function addToWishlist(variantId: string): Promise<WishlistItem> {
  const { data } = await apiClient.post<WishlistItem>('/marketplace/wishlist/', {
    variant_id: variantId,
  })
  return data
}

export async function removeFromWishlist(itemId: string): Promise<void> {
  await apiClient.delete(`/marketplace/wishlist/${itemId}/`)
}
