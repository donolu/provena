import type { Metadata } from 'next'
import type { PaginatedResponse, Product } from '@/lib/api/types'
import CataloguePage from './_client'

export const metadata: Metadata = {
  title: 'Shop | Provena',
  description: 'Browse fresh produce, artisan goods, and more from verified suppliers.',
}

export const revalidate = 60

async function fetchInitialProducts(): Promise<PaginatedResponse<Product> | undefined> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
  try {
    const res = await fetch(`${base}/api/v1/catalogue/products/`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) return undefined
    return res.json() as Promise<PaginatedResponse<Product>>
  } catch {
    return undefined
  }
}

export default async function CatalogueServerPage() {
  const initialProducts = await fetchInitialProducts()
  return <CataloguePage initialProducts={initialProducts} />
}
