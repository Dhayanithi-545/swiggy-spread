import { useEffect, useState } from 'react'

// State that survives a refresh. All "simulate it locally" features
// (carts, favorites, saved plans, recent searches) sit on this.
export function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(() => {
    try {
      const raw = window.localStorage.getItem(key)
      return raw !== null ? JSON.parse(raw) : initialValue
    } catch {
      return initialValue
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch {
      /* storage full or blocked — state still works in-memory */
    }
  }, [key, value])

  return [value, setValue]
}
