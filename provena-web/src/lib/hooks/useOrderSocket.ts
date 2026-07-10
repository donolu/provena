'use client'

import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '')
const WS_BASE = API_BASE.replace(/^https/, 'wss').replace(/^http/, 'ws')

export function useOrderSocket(reference: string, accessToken: string | null) {
  const qc = useQueryClient()

  useEffect(() => {
    if (!accessToken || !reference) return

    const url = `${WS_BASE}/ws/orders/${reference}/?token=${accessToken}`
    const ws = new WebSocket(url)

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

    return () => {
      ws.close()
    }
  }, [reference, accessToken, qc])
}
