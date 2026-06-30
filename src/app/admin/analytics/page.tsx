'use client'

import { useQuery } from '@tanstack/react-query'
import { getSalesSummary, getRevenueOverTime, getTopProducts, getSupplierPerformance } from '@/lib/api/admin'

export default function AnalyticsPage() {
  const { data: summary } = useQuery({
    queryKey: ['admin', 'analytics', 'sales'],
    queryFn: () => getSalesSummary({ days: 14 }),
  })

  const { data: revenueData } = useQuery({
    queryKey: ['admin', 'analytics', 'revenue-over-time'],
    queryFn: () => getRevenueOverTime({ days: 14 }),
  })

  const { data: topProducts } = useQuery({
    queryKey: ['admin', 'analytics', 'top-products'],
    queryFn: () => getTopProducts({ limit: 5 }),
  })

  const { data: supplierPerf } = useQuery({
    queryKey: ['admin', 'analytics', 'suppliers'],
    queryFn: getSupplierPerformance,
  })

  const revenue = revenueData ?? []
  const maxRevenue = Math.max(...revenue.map((d) => parseFloat(d.revenue)), 1)

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display italic text-2xl text-forest">Analytics</h1>
        <p className="text-sm text-soil font-sans mt-0.5">Revenue · last 14 days</p>
      </div>

      <div className="bg-white rounded-lg border border-hoarfrost p-6 mb-6">
        <div className="flex items-end justify-between mb-1">
          <p className="text-[10px] uppercase tracking-[0.13em] text-soil font-sans font-medium">Daily revenue</p>
          <p className="font-mono text-xs text-soil">£{maxRevenue.toFixed(0)} peak</p>
        </div>

        {revenue.length === 0 ? (
          <div className="h-28 flex items-center justify-center">
            <p className="text-sm font-sans text-hoarfrost">No data yet.</p>
          </div>
        ) : (
          <>
            <div className="flex items-end gap-1 h-28 mt-4 mb-2">
              {revenue.map((d) => {
                const pct = (parseFloat(d.revenue) / maxRevenue) * 100
                return (
                  <div key={d.date} className="flex-1 flex flex-col items-center gap-1 group/bar" title={`${d.date}: £${d.revenue} · ${d.orders} orders`}>
                    <div
                      className="w-full bg-meadow/40 group-hover/bar:bg-meadow rounded-t-sm transition-colors duration-150 relative"
                      style={{ height: `${pct}%` }}
                    >
                      <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-forest text-white text-[9px] font-mono px-1.5 py-0.5 rounded whitespace-nowrap opacity-0 group-hover/bar:opacity-100 transition-opacity duration-150 pointer-events-none z-10">
                        £{d.revenue}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
            <div className="flex gap-1">
              {revenue.map((d, i) => (
                <div key={d.date} className="flex-1 text-center">
                  {i % 2 === 0 && (
                    <span className="text-[9px] font-mono text-soil">
                      {d.date.slice(5, 10)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        <div className="flex gap-8 mt-5 pt-5 border-t border-hoarfrost">
          <div>
            <p className="text-[10px] uppercase tracking-[0.12em] text-soil font-sans mb-1">Total revenue</p>
            <p className="font-mono text-lg font-medium text-forest">£{summary?.total_revenue ?? '—'}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-[0.12em] text-soil font-sans mb-1">Total orders</p>
            <p className="font-mono text-lg font-medium text-forest">{summary?.total_orders ?? '—'}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-[0.12em] text-soil font-sans mb-1">Avg. order value</p>
            <p className="font-mono text-lg font-medium text-forest">
              £{summary?.avg_order_value ?? '—'}
            </p>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
          <div className="px-4 py-3.5 border-b border-hoarfrost">
            <p className="text-[10px] uppercase tracking-[0.13em] text-soil font-sans font-medium">Top products by revenue</p>
          </div>
          {!topProducts || topProducts.length === 0 ? (
            <div className="px-4 py-10 text-center text-sm font-sans text-soil">No data yet.</div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium">Product</th>
                  <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium">Units</th>
                  <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium">Revenue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {topProducts.map((p, i) => (
                  <tr key={i} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] text-hoarfrost w-3">{i + 1}</span>
                        <div>
                          <p className="text-xs font-sans font-medium text-forest">{p.product_name}</p>
                          <p className="text-[10px] font-sans text-soil">{p.supplier_name}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-soil text-right">{p.units_sold}</td>
                    <td className="px-4 py-3 font-mono text-xs font-medium text-forest text-right">£{p.revenue}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="bg-white rounded-lg border border-hoarfrost overflow-hidden">
          <div className="px-4 py-3.5 border-b border-hoarfrost">
            <p className="text-[10px] uppercase tracking-[0.13em] text-soil font-sans font-medium">Supplier performance</p>
          </div>
          {!supplierPerf || supplierPerf.length === 0 ? (
            <div className="px-4 py-10 text-center text-sm font-sans text-soil">No data yet.</div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-hoarfrost">
                  <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium">Supplier</th>
                  <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium">Revenue</th>
                  <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium">Orders</th>
                  <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-[0.1em] text-soil font-sans font-medium">Pending</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hoarfrost">
                {supplierPerf.map((s, i) => (
                  <tr key={i} className="hover:bg-mist/50 transition-colors duration-100">
                    <td className="px-4 py-3 text-xs font-sans font-medium text-forest">{s.supplier_name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-forest text-right">£{s.revenue}</td>
                    <td className="px-4 py-3 font-mono text-xs text-soil text-right">{s.orders}</td>
                    <td className="px-4 py-3 font-mono text-xs text-marigold text-right">£{s.payout_pending}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
