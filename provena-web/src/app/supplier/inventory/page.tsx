'use client'

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ChevronDown, ChevronRight, Package } from 'lucide-react'

import {
  adjustStock,
  getInventory,
  getStockLots,
  getStockMovements,
  receiveStock,
  setThreshold,
} from '@/lib/api/inventory'
import type { StockLevel, StockLot, StockMovement } from '@/lib/api/types'

// ── Receive stock modal ──────────────────────────────────────────────────────

function ReceiveModal({
  variantId,
  sku,
  onClose,
}: {
  variantId: string
  sku: string
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [qty, setQty] = useState('')
  const [lot, setLot] = useState('')
  const [expiry, setExpiry] = useState('')
  const [notes, setNotes] = useState('')

  const mutation = useMutation<StockLevel, Error, void>({
    mutationFn: async () =>
      receiveStock(variantId, {
        quantity: Number(qty),
        lot_number: lot || undefined,
        expires_at: expiry || null,
        notes: notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory'] })
      qc.invalidateQueries({ queryKey: ['inventory-lots', variantId] })
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-forest mb-4">Receive stock - {sku}</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Quantity *</label>
            <input
              type="number"
              min="1"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-forest"
              placeholder="0"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Lot number</label>
            <input
              type="text"
              value={lot}
              onChange={(e) => setLot(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-forest"
              placeholder="e.g. LOT-2026-07"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Expiry date</label>
            <input
              type="date"
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-forest"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-forest"
              placeholder="Optional"
            />
          </div>
        </div>

        {mutation.isError && (
          <p className="mt-3 text-sm text-red-600">{(mutation.error as Error).message}</p>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!qty || mutation.isPending}
            className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white disabled:opacity-50 hover:bg-forest/90"
          >
            {mutation.isPending ? 'Saving...' : 'Confirm receipt'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Adjust stock modal ───────────────────────────────────────────────────────

function AdjustModal({
  variantId,
  sku,
  currentAvailable,
  onClose,
}: {
  variantId: string
  sku: string
  currentAvailable: number
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [delta, setDelta] = useState('')
  const [notes, setNotes] = useState('')

  const mutation = useMutation<StockLevel, Error, void>({
    mutationFn: async () => adjustStock(variantId, { delta: Number(delta), notes }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory'] })
      onClose()
    },
  })

  const preview = delta ? currentAvailable + Number(delta) : currentAvailable

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-forest mb-1">Adjust stock - {sku}</h2>
        <p className="text-sm text-gray-500 mb-4">Current available: {currentAvailable}</p>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Delta (+ to add, - to remove) *
            </label>
            <input
              type="number"
              value={delta}
              onChange={(e) => setDelta(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-forest"
              placeholder="-5 or +10"
            />
            {delta && (
              <p className="mt-1 text-xs text-gray-500">
                After adjustment: <strong>{preview}</strong>
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Reason *</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-forest"
              placeholder="e.g. Stock count correction"
            />
          </div>
        </div>

        {mutation.isError && (
          <p className="mt-3 text-sm text-red-600">{(mutation.error as Error).message}</p>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!delta || !notes || mutation.isPending}
            className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white disabled:opacity-50 hover:bg-forest/90"
          >
            {mutation.isPending ? 'Saving...' : 'Apply adjustment'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Expanded row: lots + movements tabs ─────────────────────────────────────

function ExpandedInventoryRow({ variantId }: { variantId: string }) {
  const [tab, setTab] = useState<'lots' | 'movements'>('lots')

  const expiryThreshold = useMemo(() => {
    const d = new Date()
    d.setDate(d.getDate() + 3)
    return d
  }, [])

  const { data: lotsPage, isLoading: lotsLoading } = useQuery({
    queryKey: ['inventory-lots', variantId],
    queryFn: () => getStockLots(variantId),
    enabled: tab === 'lots',
  })
  const lots = lotsPage?.results ?? []

  const { data: movementsPage, isLoading: movementsLoading } = useQuery({
    queryKey: ['inventory-movements', variantId],
    queryFn: () => getStockMovements(variantId),
    enabled: tab === 'movements',
  })
  const movements = movementsPage?.results ?? []

  return (
    <div className="bg-gray-50 border-t px-6 py-4">
      <div className="flex gap-4 mb-4 border-b">
        {(['lots', 'movements'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 text-xs font-medium capitalize border-b-2 transition-colors ${
              tab === t ? 'border-forest text-forest' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'lots' ? 'Stock lots' : 'Movement history'}
          </button>
        ))}
      </div>

      {tab === 'lots' && (
        <>
          {lotsLoading && <p className="text-xs text-gray-500">Loading...</p>}
          {!lotsLoading && lots.length === 0 && (
            <p className="text-xs text-gray-500">No lots recorded yet.</p>
          )}
          {lots.length > 0 && (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-1.5 font-medium">Lot</th>
                  <th className="pb-1.5 font-medium text-right">Received</th>
                  <th className="pb-1.5 font-medium text-right">Remaining</th>
                  <th className="pb-1.5 font-medium">Expiry</th>
                  <th className="pb-1.5 font-medium">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {lots.map((lot: StockLot) => {
                  const isExpiring =
                    lot.expires_at && new Date(lot.expires_at) <= expiryThreshold
                  return (
                    <tr key={lot.id}>
                      <td className="py-1.5 font-mono">{lot.lot_number || '-'}</td>
                      <td className="py-1.5 text-right">{lot.quantity_received}</td>
                      <td className="py-1.5 text-right">{lot.quantity_remaining}</td>
                      <td className={`py-1.5 ${isExpiring ? 'text-red-600 font-medium' : ''}`}>
                        {lot.expires_at
                          ? new Date(lot.expires_at).toLocaleDateString('en-GB')
                          : '-'}
                        {isExpiring && ' ⚠'}
                      </td>
                      <td className="py-1.5 text-gray-500">{lot.notes || '-'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </>
      )}

      {tab === 'movements' && (
        <>
          {movementsLoading && <p className="text-xs text-gray-500">Loading...</p>}
          {!movementsLoading && movements.length === 0 && (
            <p className="text-xs text-gray-500">No movements recorded yet.</p>
          )}
          {movements.length > 0 && (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-1.5 font-medium">Type</th>
                  <th className="pb-1.5 font-medium text-right">Qty</th>
                  <th className="pb-1.5 font-medium text-right">After</th>
                  <th className="pb-1.5 font-medium">Reference</th>
                  <th className="pb-1.5 font-medium">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {movements.map((m: StockMovement) => (
                  <tr key={m.id}>
                    <td className="py-1.5">{m.movement_type_display}</td>
                    <td className={`py-1.5 text-right font-mono ${m.quantity < 0 ? 'text-red-600' : 'text-green-700'}`}>
                      {m.quantity > 0 ? '+' : ''}{m.quantity}
                    </td>
                    <td className="py-1.5 text-right font-mono">{m.quantity_after}</td>
                    <td className="py-1.5 font-mono text-gray-500">{m.reference || '-'}</td>
                    <td className="py-1.5 text-gray-500">
                      {new Date(m.created_at).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function SupplierInventoryPage() {
  const qc = useQueryClient()
  const [showLowStockOnly, setShowLowStockOnly] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [receiveModal, setReceiveModal] = useState<StockLevel | null>(null)
  const [adjustModal, setAdjustModal] = useState<StockLevel | null>(null)

  const { data: inventory = [], isLoading } = useQuery({
    queryKey: ['inventory', showLowStockOnly],
    queryFn: () => getInventory(showLowStockOnly || undefined),
  })

  const thresholdMutation = useMutation<
    StockLevel,
    Error,
    { variantId: string; threshold: number }
  >({
    mutationFn: ({ variantId, threshold }) => setThreshold(variantId, threshold),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory'] }),
  })

  const lowStockCount = inventory.filter((s) => s.is_low_stock).length

  return (
    <div className="p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-forest">Inventory</h1>
          {lowStockCount > 0 && (
            <p className="mt-1 flex items-center gap-1.5 text-sm text-amber-700">
              <AlertTriangle className="h-4 w-4" />
              {lowStockCount} variant{lowStockCount > 1 ? 's' : ''} below threshold
            </p>
          )}
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showLowStockOnly}
            onChange={(e) => setShowLowStockOnly(e.target.checked)}
            className="rounded border-gray-300 text-forest focus:ring-forest"
          />
          <span className="text-sm text-gray-700">Low stock only</span>
        </label>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 bg-gray-100 animate-pulse rounded-xl" />
          ))}
        </div>
      )}

      {!isLoading && inventory.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Package className="h-10 w-10 text-gray-300 mb-4" />
          <p className="font-medium text-gray-700">
            {showLowStockOnly ? 'No low-stock items' : 'No inventory records yet'}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Stock levels are created automatically when you add product variants.
          </p>
        </div>
      )}

      {!isLoading && inventory.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b text-xs font-semibold uppercase tracking-wide text-gray-500 text-left">
                <th className="px-4 py-3 w-8" />
                <th className="px-4 py-3">Product / SKU</th>
                <th className="px-4 py-3 text-right">Available</th>
                <th className="px-4 py-3 text-right">Reserved</th>
                <th className="px-4 py-3 text-right">On hand</th>
                <th className="px-4 py-3 text-right">Threshold</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {inventory.map((stock) => (
                <>
                  <tr
                    key={stock.id}
                    className={`border-b last:border-0 ${stock.is_low_stock ? 'bg-amber-50' : ''}`}
                  >
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setExpanded(expanded === stock.id ? null : stock.id)}
                        className="text-gray-400 hover:text-forest"
                      >
                        {expanded === stock.id ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-forest">{stock.product_name}</p>
                      <p className="font-mono text-xs text-gray-500">{stock.variant_sku}</p>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums font-medium">
                      {stock.is_low_stock ? (
                        <span className="text-amber-700 font-semibold">
                          {stock.quantity_available} ⚠
                        </span>
                      ) : (
                        stock.quantity_available
                      )}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-500">
                      {stock.quantity_reserved}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-500">
                      {stock.quantity_on_hand}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <input
                        type="number"
                        min="0"
                        defaultValue={stock.low_stock_threshold}
                        onBlur={(e) => {
                          const val = Number(e.target.value)
                          if (val !== stock.low_stock_threshold) {
                            thresholdMutation.mutate({
                              variantId: stock.id,
                              threshold: val,
                            })
                          }
                        }}
                        className="w-16 rounded border border-gray-300 px-2 py-1 text-right text-xs focus:outline-none focus:ring-1 focus:ring-forest"
                      />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setReceiveModal(stock)}
                          className="rounded-lg bg-forest px-3 py-1 text-xs font-medium text-white hover:bg-forest/90"
                        >
                          Receive
                        </button>
                        <button
                          onClick={() => setAdjustModal(stock)}
                          className="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                        >
                          Adjust
                        </button>
                      </div>
                    </td>
                  </tr>

                  {expanded === stock.id && (
                    <tr key={`${stock.id}-expanded`}>
                      <td colSpan={7} className="p-0">
                        <ExpandedInventoryRow variantId={stock.id} />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {receiveModal && (
        <ReceiveModal
          variantId={receiveModal.id}
          sku={receiveModal.variant_sku}
          onClose={() => setReceiveModal(null)}
        />
      )}

      {adjustModal && (
        <AdjustModal
          variantId={adjustModal.id}
          sku={adjustModal.variant_sku}
          currentAvailable={adjustModal.quantity_available}
          onClose={() => setAdjustModal(null)}
        />
      )}
    </div>
  )
}
