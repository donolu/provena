import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProductCard } from '../product-card'
import type { Product } from '@/lib/api/types'

vi.mock('next/link', () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}))

const baseProduct: Product = {
  id: 'prod-1',
  name: 'Organic Apples',
  slug: 'organic-apples',
  description: 'Fresh apples',
  status: 'ACTIVE',
  is_featured: false,
  supplier_slug: 'farm-fresh',
  supplier_name: 'Farm Fresh',
  category_slug: 'fruit',
  category_name: 'Fruit',
  variants: [
    {
      id: 'var-1',
      name: '1kg bag',
      sku: 'OA-1KG',
      price: '3.50',
      compare_at_price: null,
      weight_grams: 1000,
      is_active: true,
      on_sale: false,
      discount_percent: null,
    },
  ],
  images: [],
  average_rating: null,
  review_count: 0,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('ProductCard', () => {
  it('renders the product name', () => {
    render(
      <ProductCard
        product={baseProduct}
        inWishlist={false}
        onAddToCart={vi.fn()}
        onToggleWishlist={vi.fn()}
      />,
    )
    expect(screen.getByText('Organic Apples')).toBeInTheDocument()
  })

  it('does not show star rating when average_rating is null', () => {
    render(
      <ProductCard
        product={baseProduct}
        inWishlist={false}
        onAddToCart={vi.fn()}
        onToggleWishlist={vi.fn()}
      />,
    )
    expect(screen.queryByText(/★/)).toBeNull()
  })

  it('shows star rating when average_rating and review_count are set', () => {
    const product = { ...baseProduct, average_rating: 4.2, review_count: 17 }
    render(
      <ProductCard
        product={product}
        inWishlist={false}
        onAddToCart={vi.fn()}
        onToggleWishlist={vi.fn()}
      />,
    )
    expect(screen.getByText('4.2 (17)')).toBeInTheDocument()
    // Rounded to 4 stars: 4 filled + 1 empty
    expect(screen.getByText('★★★★☆')).toBeInTheDocument()
  })

  it('does not show star rating when review_count is 0', () => {
    const product = { ...baseProduct, average_rating: 4.5, review_count: 0 }
    render(
      <ProductCard
        product={product}
        inWishlist={false}
        onAddToCart={vi.fn()}
        onToggleWishlist={vi.fn()}
      />,
    )
    expect(screen.queryByText(/★/)).toBeNull()
  })

  it('calls onToggleWishlist with variant id when heart button clicked', () => {
    const onToggleWishlist = vi.fn()
    render(
      <ProductCard
        product={baseProduct}
        inWishlist={false}
        onAddToCart={vi.fn()}
        onToggleWishlist={onToggleWishlist}
      />,
    )
    const heartBtn = screen.getByRole('button', { name: /wishlist/i })
    fireEvent.click(heartBtn)
    expect(onToggleWishlist).toHaveBeenCalledWith('var-1')
  })

  it('calls onAddToCart with variant id when add to cart button clicked', () => {
    const onAddToCart = vi.fn()
    render(
      <ProductCard
        product={baseProduct}
        inWishlist={false}
        onAddToCart={onAddToCart}
        onToggleWishlist={vi.fn()}
      />,
    )
    const addBtn = screen.getByRole('button', { name: /add to cart/i })
    fireEvent.click(addBtn)
    expect(onAddToCart).toHaveBeenCalledWith('var-1')
  })
})
