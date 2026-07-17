import type { Order } from '@/lib/api/types'

function Row({
  label,
  value,
  emphasis = false,
  muted = false,
}: {
  label: string
  value: string
  emphasis?: boolean
  muted?: boolean
}) {
  return (
    <div className="flex items-baseline justify-between">
      <span
        className={`font-sans ${emphasis ? 'text-sm text-soil' : 'text-xs text-soil'} ${
          muted ? 'text-hoarfrost' : ''
        }`}
      >
        {label}
      </span>
      <span
        className={`font-mono ${
          emphasis ? 'text-base font-semibold text-forest' : 'text-xs text-forest'
        } ${muted ? 'text-soil' : ''}`}
      >
        {value}
      </span>
    </div>
  )
}

/** Money breakdown (goods / discount / shipping / VAT / total) for a placed order. */
export function OrderBreakdown({ order }: { order: Order }) {
  const hasDiscount = Number(order.discount_amount) > 0
  const shipping = Number(order.shipping_amount) === 0 ? 'Free' : `£${order.shipping_amount}`
  return (
    <div className="space-y-2">
      <Row label="Goods" value={`£${order.goods_subtotal}`} />
      {hasDiscount && (
        <Row
          label={order.discount_code ? `Discount (${order.discount_code})` : 'Discount'}
          value={`-£${order.discount_amount}`}
        />
      )}
      <Row label="Shipping" value={shipping} />
      <Row label="Includes VAT" value={`£${order.vat_amount}`} muted />
      <div className="pt-2 mt-1 border-t border-hoarfrost">
        <Row label="Total" value={`£${order.total_amount}`} emphasis />
      </div>
    </div>
  )
}
