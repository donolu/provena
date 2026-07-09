import type { Metadata } from 'next'
import type { PaginatedResponse, Product, PublicSupplier } from '@/lib/api/types'
import SupplierStorefrontPage from './_client'

export const revalidate = 60

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function fetchSupplier(slug: string): Promise<PublicSupplier | undefined> {
  try {
    const res = await fetch(`${BASE}/api/v1/suppliers/${slug}/`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) return undefined
    return res.json() as Promise<PublicSupplier>
  } catch {
    return undefined
  }
}

async function fetchSupplierProducts(slug: string): Promise<Product[]> {
  try {
    const res = await fetch(`${BASE}/api/v1/catalogue/products/?supplier=${slug}&page_size=100`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) return []
    const data = (await res.json()) as PaginatedResponse<Product>
    return data.results
  } catch {
    return []
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>
}): Promise<Metadata> {
  const { slug } = await params
  const supplier = await fetchSupplier(slug)
  if (!supplier) return { title: 'Supplier | Provena' }
  return {
    title: `${supplier.business_name} | Provena`,
    description: supplier.description
      ? supplier.description.slice(0, 160)
      : `Shop ${supplier.product_count} product${supplier.product_count !== 1 ? 's' : ''} from ${supplier.business_name} on Provena.`,
    openGraph: {
      title: supplier.business_name,
      description: supplier.description?.slice(0, 160) ?? '',
      images: supplier.logo_url ? [{ url: supplier.logo_url, alt: supplier.business_name }] : [],
    },
  }
}

export async function generateStaticParams(): Promise<{ slug: string }[]> {
  try {
    const res = await fetch(`${BASE}/api/v1/suppliers/`, {
      next: { revalidate: 3600 },
    })
    if (!res.ok) return []
    const data = (await res.json()) as PublicSupplier[]
    return data.map((s) => ({ slug: s.slug }))
  } catch {
    return []
  }
}

export default async function SupplierStorefrontServerPage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params
  const [supplier, products] = await Promise.all([
    fetchSupplier(slug),
    fetchSupplierProducts(slug),
  ])
  return (
    <SupplierStorefrontPage
      params={params}
      initialSupplier={supplier}
      initialProducts={products}
    />
  )
}
