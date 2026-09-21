import { useEffect, useState } from 'react'

// Simulates a network fetch so skeleton loaders get their moment.
// Re-triggers when `dep` changes (e.g. a filter or route param).
export function useFakeLoading(ms = 650, dep = null) {
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    setLoading(true)
    const t = setTimeout(() => setLoading(false), ms)
    return () => clearTimeout(t)
  }, [ms, dep])
  return loading
}
