'use client'

interface CategoryTab {
  id: string
  name: string
  slug: string
}

interface CategoryTabsProps {
  categories: CategoryTab[]
  active: string
  onSelect: (slug: string) => void
}

export function CategoryTabs({ categories, active, onSelect }: CategoryTabsProps) {
  return (
    <div className="border-b border-hoarfrost bg-mist/95 backdrop-blur-sm">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex overflow-x-auto no-scrollbar" role="tablist">
          {categories.map((cat) => {
            const isActive = active === cat.slug
            return (
              <button
                key={cat.id}
                role="tab"
                aria-selected={isActive}
                onClick={() => onSelect(cat.slug)}
                className={[
                  'relative flex-shrink-0 px-4 py-3.5 text-sm whitespace-nowrap transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-meadow focus-visible:ring-offset-1',
                  isActive ? 'text-forest font-medium' : 'text-soil hover:text-forest',
                ].join(' ')}
              >
                {cat.name}
                {isActive && (
                  <span
                    aria-hidden="true"
                    className="absolute bottom-0 left-3 right-3 h-0.5 bg-forest rounded-full"
                  />
                )}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
