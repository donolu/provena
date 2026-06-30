import type { Category, Product, Supplier } from '@/types'

export const categories: Category[] = [
  { id: 'all',      name: 'All',      slug: 'all' },
  { id: 'produce',  name: 'Produce',  slug: 'produce' },
  { id: 'dairy',    name: 'Dairy',    slug: 'dairy' },
  { id: 'grains',   name: 'Grains',   slug: 'grains' },
  { id: 'pantry',   name: 'Pantry',   slug: 'pantry' },
  { id: 'seasonal', name: 'Seasonal', slug: 'seasonal' },
]

const freshFarms: Supplier = {
  id: 's1',
  business_name: 'Fresh Farms',
  slug: 'fresh-farms',
  location: 'Somerset, England',
  rating: 4.8,
}

const greenValleyDairy: Supplier = {
  id: 's2',
  business_name: 'Green Valley Dairy',
  slug: 'green-valley-dairy',
  location: 'Yorkshire, UK',
  rating: 4.6,
}

const grainAndCo: Supplier = {
  id: 's3',
  business_name: 'Grain & Co.',
  slug: 'grain-and-co',
  location: 'Norfolk, UK',
  rating: 4.8,
}

const wildRootPantry: Supplier = {
  id: 's4',
  business_name: 'Wild Root Pantry',
  slug: 'wild-root-pantry',
  location: 'Devon, England',
  rating: 4.7,
}

export const products: Product[] = [
  // ── Fresh Farms (Produce) ────────────────────────────────────────
  {
    id: 'p1',
    name: 'Carrots',
    category_slug: 'produce',
    supplier: freshFarms,
    review_count: 24,
    variants: [{ id: 'v1', name: '1 kg', sku: 'CARR-1KG', price: '2.50', unit: 'kg', stock_available: 48 }],
  },
  {
    id: 'p2',
    name: 'Spinach',
    category_slug: 'produce',
    supplier: freshFarms,
    review_count: 18,
    variants: [{ id: 'v2', name: '200 g', sku: 'SPIN-200G', price: '1.80', unit: 'bag', stock_available: 31 }],
  },
  {
    id: 'p3',
    name: 'Tenderstem Broccoli',
    category_slug: 'produce',
    supplier: freshFarms,
    review_count: 31,
    variants: [{ id: 'v3', name: '250 g', sku: 'BRCL-250G', price: '2.40', unit: 'bunch', stock_available: 6 }],
  },
  // ── Green Valley Dairy ───────────────────────────────────────────
  {
    id: 'p4',
    name: 'Farmhouse Cheddar',
    category_slug: 'dairy',
    supplier: greenValleyDairy,
    review_count: 41,
    variants: [{ id: 'v4', name: '400 g', sku: 'CHDR-400G', price: '4.20', unit: 'block', stock_available: 22 }],
  },
  {
    id: 'p5',
    name: 'Cultured Butter',
    category_slug: 'dairy',
    supplier: greenValleyDairy,
    review_count: 29,
    variants: [{ id: 'v5', name: '250 g', sku: 'BUTR-250G', price: '2.90', unit: 'pack', stock_available: 15 }],
  },
  {
    id: 'p6',
    name: 'Crème Fraîche',
    category_slug: 'dairy',
    supplier: greenValleyDairy,
    review_count: 12,
    variants: [{ id: 'v6', name: '300 ml', sku: 'CREME-300', price: '2.10', unit: 'pot', stock_available: 0 }],
  },
  // ── Grain & Co. (Grains) ─────────────────────────────────────────
  {
    id: 'p7',
    name: 'Sourdough Flour',
    category_slug: 'grains',
    supplier: grainAndCo,
    review_count: 37,
    variants: [{ id: 'v7', name: '1 kg', sku: 'FLOUR-1KG', price: '3.20', unit: 'kg', stock_available: 56 }],
  },
  {
    id: 'p8',
    name: 'Rolled Oats',
    category_slug: 'grains',
    supplier: grainAndCo,
    review_count: 22,
    variants: [{ id: 'v8', name: '500 g', sku: 'OATS-500G', price: '1.90', unit: 'bag', stock_available: 44 }],
  },
  {
    id: 'p9',
    name: 'Spelt Berries',
    category_slug: 'grains',
    supplier: grainAndCo,
    review_count: 8,
    variants: [{ id: 'v9', name: '750 g', sku: 'SPLT-750G', price: '4.50', unit: 'bag', stock_available: 4 }],
  },
  // ── Wild Root Pantry ─────────────────────────────────────────────
  {
    id: 'p10',
    name: 'Raw Wildflower Honey',
    category_slug: 'pantry',
    supplier: wildRootPantry,
    review_count: 53,
    variants: [{ id: 'v10', name: '340 g', sku: 'HNYWF-340', price: '8.50', unit: 'jar', stock_available: 19 }],
  },
  {
    id: 'p11',
    name: 'Apple Cider Vinegar',
    category_slug: 'pantry',
    supplier: wildRootPantry,
    review_count: 17,
    variants: [{ id: 'v11', name: '500 ml', sku: 'ACV-500', price: '5.20', unit: 'bottle', stock_available: 27 }],
  },
  {
    id: 'p12',
    name: 'Cold-pressed Rapeseed Oil',
    category_slug: 'pantry',
    supplier: wildRootPantry,
    review_count: 9,
    variants: [{ id: 'v12', name: '500 ml', sku: 'RPSD-500', price: '6.80', unit: 'bottle', stock_available: 11 }],
  },
]

export function groupBySupplier(items: Product[]): { supplier: Supplier; products: Product[] }[] {
  const map = new Map<string, { supplier: Supplier; products: Product[] }>()
  for (const product of items) {
    const key = product.supplier.id
    if (!map.has(key)) map.set(key, { supplier: product.supplier, products: [] })
    map.get(key)!.products.push(product)
  }
  return Array.from(map.values())
}
