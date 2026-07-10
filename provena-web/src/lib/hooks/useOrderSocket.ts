'use client'

import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getWsTicket } from '@/lib/api/orders'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '')
const WS_BASE = API_BASE.replace(/^https/, 'wss').replace(/^http/, 'ws')

export function useOrderSocket(reference: string, accessToken: string | null) {
  const qc = useQueryClient()

  useEffect(() => {
    if (!accessToken || !reference) return

    let ws: WebSocket | null = null
    let cancelled = false

    getWsTicket()
      .then((ticket) => {
        if (cancelled) return
        ws = new WebSocket(`${WS_BASE}/ws/orders/${reference}/?ticket=${ticket}`)
        ws.onmessage = (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data as string)
            if (data.type === 'order_status') {
              qc.invalidateQueries({ queryKey: ['order', reference] })
            }
          } catch {
            // malformed message; ignore
          }
        }
      })
      .catch(() => {
        // ticket fetch failed (e.g. logged out); skip WS connection
      })

    return () => {
      cancelled = true
      ws?.close()
    }
  }, [reference, accessToken, qc])
}
