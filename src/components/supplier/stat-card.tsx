import { TrendingDown, TrendingUp } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string
  prefix?: string
  suffix?: string
  trend?: { pct: number; label: string }
  icon: LucideIcon
  alert?: boolean
}

export function StatCard({ label, value, prefix, suffix, trend, icon: Icon, alert }: StatCardProps) {
  const isUp = trend && trend.pct >= 0

  return (
    <div className={`bg-white rounded-lg p-5 border ${alert ? 'border-marigold/50' : 'border-hoarfrost'}`}>
      <div className="flex items-start justify-between mb-3">
        <p className="text-[10px] uppercase tracking-[0.13em] text-soil font-sans font-medium">
          {label}
        </p>
        <Icon
          className={`w-4 h-4 flex-shrink-0 ${alert ? 'text-marigold' : 'text-hoarfrost'}`}
          strokeWidth={1.5}
        />
      </div>

      <p className="font-mono text-[26px] font-medium text-forest leading-none">
        {prefix}<span>{value}</span>{suffix && <span className="text-base font-normal text-soil ml-0.5">{suffix}</span>}
      </p>

      {trend && (
        <div className={`flex items-center gap-1 mt-2 ${isUp ? 'text-meadow' : 'text-soil'}`}>
          {isUp
            ? <TrendingUp className="w-3 h-3" strokeWidth={2} />
            : <TrendingDown className="w-3 h-3" strokeWidth={2} />
          }
          <span className="text-[11px] font-sans">
            {isUp ? '+' : ''}{trend.pct}% {trend.label}
          </span>
        </div>
      )}
    </div>
  )
}
