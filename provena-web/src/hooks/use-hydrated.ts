import { useSyncExternalStore } from 'react'

// Hydration-safe "is this the client?" flag: false during SSR and the first
// client render (so it matches the server markup), true on every render after
// mount. Lets a component defer client-only rendering without a hydration
// mismatch and without calling setState from an effect.
const subscribe = () => () => {}

export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  )
}
