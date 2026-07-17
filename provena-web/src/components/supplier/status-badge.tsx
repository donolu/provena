const STYLES: Record<string, string> = {
  // Order statuses
  PENDING:    'bg-marigold/15 text-[#7A5A08]',
  CONFIRMED:  'bg-meadow/15 text-[#245C38]',
  DISPATCHED: 'bg-forest/10 text-forest',
  DELIVERED:  'bg-meadow/20 text-[#1A4530]',
  CANCELLED:  'bg-soil/10 text-soil',
  // Product statuses
  ACTIVE:   'bg-meadow/15 text-[#245C38]',
  DRAFT:    'bg-marigold/15 text-[#7A5A08]',
  ARCHIVED: 'bg-hoarfrost text-soil',
  // Payout statuses
  PROCESSING: 'bg-marigold/10 text-[#7A5A08]',
  PAID:       'bg-meadow/20 text-[#1A4530]',
  FAILED:     'bg-red-50 text-red-700',
  REVERSED:   'bg-soil/10 text-soil',
}

const LABELS: Record<string, string> = {
  DISPATCHED: 'Dispatched',
  DELIVERED:  'Delivered',
  CONFIRMED:  'Confirmed',
  CANCELLED:  'Cancelled',
  PENDING:    'Pending',
  ACTIVE:     'Active',
  DRAFT:      'Draft',
  ARCHIVED:   'Archived',
  PROCESSING: 'Processing',
  PAID:       'Paid',
  FAILED:     'Failed',
  REVERSED:   'Reversed',
}

export function StatusBadge({ status }: { status: string }) {
  const style = STYLES[status] ?? 'bg-hoarfrost text-soil'
  const label = LABELS[status] ?? status
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-sans font-semibold uppercase tracking-wide ${style}`}>
      {label}
    </span>
  )
}
