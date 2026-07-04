import type { Metadata } from 'next'
import type { Product } from '@/lib/api/types'
import ProductDetailPage from './_client'

export const revalidate = 60

async function fetchProduct(slug: string): Promise<Product | undefined> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
  try {
    const res = await fetch(`${base}/api/v1/catalogue/products/${slug}/`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) return undefined
    return res.json() as Promise<Product>
  } catch {
    return undefined
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>
}): Promise<Metadata> {
  const { slug } = await params
  const product = await fetchProduct(slug)
  if (!product) return { title: 'Product | Provena' }
  return {
    title: `${product.name} | Provena`,
    description: product.description
      ? product.description.slice(0, 160)
      : `Buy ${product.name} from ${product.supplier_name} on Provena.`,
    openGraph: {
      title: product.name,
      description: product.description?.slice(0, 160) ?? '',
      images: product.images[0] ? [{ url: product.images[0].url, alt: product.images[0].alt_text }] : [],
    },
  }
}

export async function generateStaticParams(): Promise<{ slug: string }[]> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
  try {
    const res = await fetch(`${base}/api/v1/catalogue/products/?page_size=200`, {
      next: { revalidate: 3600 },
    })
    if (!res.ok) return []
    const data = await res.json() as { results: Product[] }
    return data.results.map((p) => ({ slug: p.slug }))
  } catch {
    return []
  }
}

export default async function ProductDetailServerPage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params
  const product = await fetchProduct(slug)
  return <ProductDetailPage params={params} initialProduct={product} />
}
