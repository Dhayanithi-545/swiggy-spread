import { createContext, useContext, useMemo } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'

// Multi-cart state — Spread's whole point. One cart per (platform,
// vendor): browsing a restaurant builds a Food cart for it, Instamart
// items pool into one Instamart cart, and approving a plan creates one
// timed cart per course. Purely local; nothing talks to a backend.

const CartContext = createContext(null)

const cartKey = (platform, vendorId) => `${platform}:${vendorId || 'instamart'}`

export function CartProvider({ children }) {
  const [carts, setCarts] = useLocalStorage('spread_carts', [])
  const [savedPlans, setSavedPlans] = useLocalStorage('spread_plans', [])

  const api = useMemo(() => {
    const addItem = (source, item, qty = 1) => {
      // Pure updater — StrictMode runs these twice, so no mutation of prev.
      setCarts((prev) => {
        const key = cartKey(source.platform, source.vendorId)
        const newLine = {
          id: item.id,
          name: item.name,
          price: item.price,
          veg: item.veg,
          emoji: item.emoji || '🍽️',
          qty,
        }
        const existing = prev.find((c) => c.key === key)
        if (!existing) {
          return [
            ...prev,
            {
              key,
              id: key,
              platform: source.platform,
              vendorId: source.vendorId || null,
              vendorName: source.vendorName,
              etaMin: source.etaMin,
              slot: source.slot || null,
              orderAt: source.orderAt ?? null,
              eatAt: source.eatAt ?? null,
              fromPlan: source.fromPlan || null,
              items: [newLine],
            },
          ]
        }
        return prev.map((c) => {
          if (c.key !== key) return c
          const hasLine = c.items.some((x) => x.id === item.id)
          const items = hasLine
            ? c.items.map((x) => (x.id === item.id ? { ...x, qty: x.qty + qty } : x))
            : [...c.items, newLine]
          return { ...c, items }
        })
      })
    }

    const setQty = (cartId, itemId, qty) => {
      setCarts((prev) =>
        prev
          .map((c) =>
            c.id !== cartId
              ? c
              : {
                  ...c,
                  items: c.items
                    .map((x) => (x.id === itemId ? { ...x, qty } : x))
                    .filter((x) => x.qty > 0),
                },
          )
          .filter((c) => c.items.length > 0),
      )
    }

    const removeCart = (cartId) => setCarts((prev) => prev.filter((c) => c.id !== cartId))
    const clearAll = () => setCarts([])

    // Approving a plan: one cart per course, timing attached.
    const fillFromPlan = (plan) => {
      setCarts((prev) => {
        const next = prev.filter((c) => c.fromPlan !== plan.id)
        for (const course of plan.courses) {
          next.push({
            key: `plan:${plan.id}:${course.slot}`,
            id: `plan:${plan.id}:${course.slot}`,
            platform: course.platform,
            vendorId: course.vendorId || null,
            vendorName: course.vendorName,
            etaMin: course.etaMin,
            slot: course.slot,
            orderAt: course.orderAt,
            eatAt: course.eatAt,
            fromPlan: plan.id,
            planBudget: plan.budget,
            items: course.items.map((x) => ({ ...x })),
          })
        }
        return next
      })
      setSavedPlans((prev) => [
        { ...plan, status: 'carts-filled' },
        ...prev.filter((p) => p.id !== plan.id),
      ])
    }

    const savePlan = (plan) =>
      setSavedPlans((prev) => [plan, ...prev.filter((p) => p.id !== plan.id)])

    return { addItem, setQty, removeCart, clearAll, fillFromPlan, savePlan }
  }, [setCarts, setSavedPlans])

  const itemCount = carts.reduce((a, c) => a + c.items.reduce((b, x) => b + x.qty, 0), 0)
  const grandTotal = carts.reduce(
    (a, c) => a + c.items.reduce((b, x) => b + x.price * x.qty, 0),
    0,
  )
  const cartFor = (platform, vendorId) =>
    carts.find((c) => c.key === cartKey(platform, vendorId))

  const value = useMemo(
    () => ({ carts, savedPlans, itemCount, grandTotal, cartFor, ...api }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [carts, savedPlans, itemCount, grandTotal, api],
  )

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart() {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used inside CartProvider')
  return ctx
}
