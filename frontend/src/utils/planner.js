// ============================================================
// planner.js — a faithful frontend port of the backend brain
// (core/conversation.py + core/portions.py + core/agent.py).
//
// Same rules, deliberately:
//  - courses come from the user; ambiguity asks, never assumes
//  - never invent a budget or a headcount — ask, with a default
//  - cap questions at 3, then proceed with stated assumptions
//  - a dinner is a spread (main + staple + bread), not 3× one dish
//  - order times are worked backwards from when food should land
//
// Pure functions over mock data. No network, no backend calls.
// ============================================================

import { restaurants } from '../data/restaurants.js'
import { getMenu } from '../data/menus.js'
import { snackPool, dessertPool } from '../data/instamart.js'
import { clamp } from './format.js'

export const ALL_SLOTS = ['snacks', 'dinner', 'dessert']
export const MAX_QUESTIONS = 3
const MIN_BUDGET = 100
const MAX_BUDGET = 100000

// Delivery reality per platform: mock ETAs, with the buffer the backend
// uses (10 min + ~20% of ETA, floored to what the README shows).
const TIMING = {
  food: { etaMin: 38, bufferMin: 20 },
  instamart: { etaMin: 15, bufferMin: 15 },
}

const DEFAULT_EAT_AT = 20 * 60 // 8:00 PM in minutes-from-midnight

// ---------------------------------------------------------- slot words

const SLOT_WORDS = {
  snacks: [
    /\bsnacks?\b/, /\bstarters?\b/, /\bappetiz?ers?\b/, /\bchips\b/,
    /\bnibbles?\b/, /\bfinger food\b/, /\bchakna\b/, /\bnamkeen\b/,
  ],
  dinner: [
    /\bdinner\b/, /\blunch\b/, /\bmeal\b/, /\bmains?\b/, /\bfood\b/,
    /\bbiryani\b/, /\bcurry\b/, /\bthali\b/, /\bpizza\b/, /\beat\b/,
    /\bsupper\b/, /\bfeast\b/, /\bparotta\b/, /\bdosa\b/, /\bnoodles?\b/,
    /\bburgers?\b/, /\bshawarma\b/,
  ],
  dessert: [
    /\bdesserts?\b/, /\bsweets?\b/, /\bcakes?\b/, /\bice cream\b/,
    /\bgulab jamun\b/, /\bpastry\b/, /\bpastries\b/, /\bbrownie/,
    /\bhalwa\b/, /\bkheer\b/, /\brasmalai\b/, /\bkulfi\b/,
  ],
}

const WHOLE_EVENING = [
  /\bwhole (evening|night|thing)\b/, /\bfull (spread|meal|course|evening)\b/,
  /\beverything\b/, /\bthree courses?\b/, /\b3 courses?\b/,
  /\bsnacks?,? (and )?dinner,? (and )?dessert/, /\bstart to finish\b/,
  /\bsort (it|everything) out\b/, /\bplan the (evening|night|party)\b/,
]

const GATHERING = [
  /\bpart(y|ies)\b/, /\bgathering\b/, /\bget.?together\b/,
  /\bfriends? (are )?(coming|over)\b/, /\bpeople (are )?coming\b/,
  /\bhaving (people|friends|guests)\b/, /\bhost(ing)?\b/,
  /\bcelebrat/, /\bbirthday\b/, /\banniversar/,
]

const DISH_HINTS = [
  'biryani', 'parotta', 'pizza', 'dosa', 'noodles', 'shawarma', 'burger',
  'kothu', 'naan', 'paneer', 'thali', 'idli', 'kulfi', 'brownie',
]

const some = (text, patterns) => patterns.some((p) => p.test(text))

// ---------------------------------------------------------- guardrail-lite

// The backend runs a rule-based guardrail on the first message AND on
// every clarify reply. This is the UI twin — enough to demo the stance.
export function checkGuardrail(text) {
  const t = (text || '').toLowerCase()
  const rules = [
    [/ignore (all|previous|prior).{0,20}(instructions|rules)/, 'That looks like a prompt-injection attempt, so I stopped.'],
    [/\b(place|confirm|submit) (the )?order\b|\bcheckout now\b|\bpay (for|now)\b/, 'Spread never places orders or moves money — I fill carts and stop. You check out in the Swiggy app.'],
    [/\brefund\b|\bchargeback\b|\bfree food\b.*\btrick\b/, 'I can only help plan and fill carts — nothing on that.'],
  ]
  for (const [pattern, reason] of rules) {
    if (pattern.test(t)) return { allowed: false, reason }
  }
  return { allowed: true, reason: '' }
}

// ---------------------------------------------------------- parsing

export function parseTimeText(text) {
  const t = (text || '').toLowerCase()
  let m = t.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)/)
  if (m) {
    let h = parseInt(m[1], 10) % 12
    if (m[3] === 'pm') h += 12
    return h * 60 + (m[2] ? parseInt(m[2], 10) : 0)
  }
  m = t.match(/\b(\d{1,2}):(\d{2})\b/)
  if (m) {
    const h = parseInt(m[1], 10)
    if (h >= 0 && h <= 23) return h * 60 + parseInt(m[2], 10)
  }
  return null
}

export function inferSlots(text) {
  const t = (text || '').toLowerCase()
  if (some(t, WHOLE_EVENING)) return { slots: [...ALL_SLOTS], confident: true }
  const named = ALL_SLOTS.filter((s) => some(t, SLOT_WORDS[s]))
  if (named.length) return { slots: named, confident: true }
  if (some(t, GATHERING)) return { slots: ['dinner'], confident: false }
  return { slots: ['dinner'], confident: false }
}

export function parseRequest(text) {
  const t = (text || '').toLowerCase()

  // guests — never invented; unknown means we ask
  let guests = 4
  let guestsKnown = false
  let m =
    t.match(/(\d+)\s*(?:friends?|people|guests?|persons?|pax|of us|folks)/) ||
    t.match(/\bfor\s+(\d+)\b/) ||
    t.match(/\bwe(?:'| a)re\s+(\d+)\b/)
  if (m) {
    guests = clamp(parseInt(m[1], 10), 1, 100)
    guestsKnown = true
  }

  // budget — same: parse or ask, never invent
  let budget = null
  m =
    t.match(/budget\s*(?:of|is|:)?\s*(?:rs\.?|₹|inr)?\s*(\d[\d,]*)/) ||
    t.match(/(?:under|within|around|about|max)\s*(?:rs\.?|₹|inr)?\s*(\d[\d,]{2,})/) ||
    t.match(/(?:rs\.?|₹|inr)\s*(\d[\d,]*)/)
  if (m) budget = clamp(parseInt(m[1].replace(/,/g, ''), 10), MIN_BUDGET, MAX_BUDGET)
  if (budget === null) {
    m = t.match(/(\d+(?:\.\d+)?)\s*k\b/)
    if (m) budget = clamp(Math.round(parseFloat(m[1]) * 1000), MIN_BUDGET, MAX_BUDGET)
  }

  // veg headcount
  let vegCount = 0
  let allVeg = false
  if (/\b(all|everyone|everybody|pure|only)\s*(?:of us\s*)?(?:are\s*)?veg(?:etarian)?s?\b/.test(t)) {
    allVeg = true
  } else {
    m = t.match(/(\d+)\s*(?:of (?:us|them)\s*)?(?:are\s*)?veg(?:etarian)?s?/)
    if (m) vegCount = parseInt(m[1], 10)
    else if (/\bveg(etarian)? (option|food|dishes)\b/.test(t)) vegCount = 1
  }
  if (allVeg) vegCount = guests

  // avoid tags — Swiggy has no "spicy" field, so names are matched later
  const avoid = []
  if (/\b(no|not|hates?|avoid|without|less|zero)\b.{0,12}\bspicy?\b|\bmild\b/.test(t)) {
    avoid.push('spicy')
  }

  // time
  const parsedTime = parseTimeText(t)
  const eatAt = parsedTime ?? DEFAULT_EAT_AT
  const timeKnown = parsedTime !== null

  // day label, purely for display
  const dayMatch = t.match(
    /\b(tonight|today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|this weekend)\b/,
  )

  const { slots, confident } = inferSlots(t)
  const dishHints = DISH_HINTS.filter((h) => t.includes(h))

  return {
    rawText: text,
    guests,
    guestsKnown,
    budget,
    vegCount: Math.min(vegCount, guests),
    allVeg,
    avoid,
    eatAt,
    timeKnown,
    dayLabel: dayMatch ? dayMatch[1] : '',
    slots,
    slotsConfident: confident,
    dishHints,
  }
}

// ---------------------------------------------------------- budget maths

// Per-head comfortable range per course (₹). Tuned so 6 guests × three
// courses lands on the backend's researched ₹2400–₹3700 window.
const PER_HEAD = {
  snacks: [100, 140],
  dinner: [210, 330],
  dessert: [90, 145],
}

export function budgetRange(guests, slots) {
  let lo = 0
  let hi = 0
  for (const s of slots) {
    lo += PER_HEAD[s][0]
    hi += PER_HEAD[s][1]
  }
  const round50 = (n) => Math.round(n / 50) * 50
  return [round50(lo * guests), round50(hi * guests)]
}

export function suggestBudget(guests, slots) {
  const [lo, hi] = budgetRange(guests, slots)
  return Math.round((lo + hi) / 2 / 100) * 100
}

const SPLIT_WEIGHTS = { snacks: 25, dinner: 50, dessert: 25 }

function budgetSplit(slots, budget) {
  const totalWeight = slots.reduce((a, s) => a + SPLIT_WEIGHTS[s], 0)
  const shares = {}
  for (const s of slots) shares[s] = Math.floor((budget * SPLIT_WEIGHTS[s]) / totalWeight)
  return shares
}

// ---------------------------------------------------------- questions

export const COURSE_CHOICES = [
  { label: 'Snacks only', slots: ['snacks'] },
  { label: 'Dinner only', slots: ['dinner'] },
  { label: 'Dessert only', slots: ['dessert'] },
  { label: 'The whole evening — snacks, dinner, dessert', slots: [...ALL_SLOTS] },
]

export function nextQuestion(req, asked) {
  if (asked.length >= MAX_QUESTIONS) return null

  if (!asked.includes('courses') && !req.slotsConfident) {
    return {
      field: 'courses',
      text: 'What should I sort out?',
      options: COURSE_CHOICES.map((c) => c.label),
      default: 'Dinner only',
      why: "I don't want to order courses you didn't ask for.",
    }
  }
  if (!asked.includes('guests') && !req.guestsKnown) {
    return {
      field: 'guests',
      text: 'How many people am I feeding?',
      options: ['2', '4', '6', '8'],
      default: '4',
      why: 'Portions and the budget I suggest both hang off this.',
    }
  }
  if (!asked.includes('time') && !req.timeKnown) {
    return {
      field: 'time',
      text: 'What time should the food be on the table?',
      options: ['7 PM', '8 PM', '9 PM'],
      default: '8 PM',
      why: 'I work backwards from this to decide when each cart orders.',
    }
  }
  if (!asked.includes('budget') && req.budget === null) {
    const [lo, hi] = budgetRange(req.guests, req.slots)
    const mid = suggestBudget(req.guests, req.slots)
    return {
      field: 'budget',
      text: `What's your budget? For ${req.guests} people and ${req.slots.join(' + ')}, ₹${lo.toLocaleString('en-IN')}–₹${hi.toLocaleString('en-IN')} is a comfortable spread.`,
      options: [`₹${lo.toLocaleString('en-IN')}`, `₹${mid.toLocaleString('en-IN')}`, `₹${hi.toLocaleString('en-IN')}`],
      default: `₹${mid.toLocaleString('en-IN')}`,
      why: 'I hold this across every cart, so I need a real number.',
    }
  }
  return null
}

function parseSlotsAnswer(answer) {
  const a = (answer || '').trim().toLowerCase()
  if (!a) return []
  if (/^(all|everything|whole evening)$/.test(a)) return [...ALL_SLOTS]
  const single = a.match(/^\s*(\d+)\s*$/)
  if (single) {
    const idx = parseInt(single[1], 10) - 1
    return COURSE_CHOICES[idx] ? [...COURSE_CHOICES[idx].slots] : []
  }
  const picked = new Set(ALL_SLOTS.filter((s) => some(a, SLOT_WORDS[s])))
  if (/whole|three/.test(a) || /snacks.+dinner.+dessert/.test(a)) {
    ALL_SLOTS.forEach((s) => picked.add(s))
  }
  return ALL_SLOTS.filter((s) => picked.has(s))
}

// Fold one answer back into the request. Empty or junk answers fall
// back to the default — pressing enter is always a valid answer.
export function applyAnswer(req, question, answer) {
  const text = (answer || '').trim() || question.default
  const next = { ...req }

  if (question.field === 'courses') {
    const slots = parseSlotsAnswer(text)
    next.slots = slots.length ? slots : parseSlotsAnswer(question.default)
    if (!next.slots.length) next.slots = ['dinner']
    next.slotsConfident = true
  } else if (question.field === 'guests') {
    const m = text.match(/\d+/)
    if (m) {
      next.guests = clamp(parseInt(m[0], 10), 1, 100)
      next.guestsKnown = true
      if (next.allVeg) next.vegCount = next.guests
    }
  } else if (question.field === 'time') {
    const parsed = parseTimeText(text)
    if (parsed !== null) {
      next.eatAt = parsed
      next.timeKnown = true
    }
  } else if (question.field === 'budget') {
    const m = text.replace(/,/g, '').match(/\d+/)
    if (m) next.budget = clamp(parseInt(m[0], 10), MIN_BUDGET, MAX_BUDGET)
  }
  return next
}

export function summariseAssumptions(req) {
  const out = []
  if (!req.slotsConfident) out.push(`assumed you wanted ${req.slots.join(' + ')}`)
  if (!req.guestsKnown) out.push(`assumed ${req.guests} people`)
  if (!req.timeKnown) out.push('assumed 8:00 PM on the table')
  if (req.budget === null) {
    out.push(`suggested a ₹${suggestBudget(req.guests, req.slots).toLocaleString('en-IN')} budget — say a number to change it`)
  }
  return out
}

// ---------------------------------------------------------- portions

// core/portions.py in one comment: one curry per 4–5 guests, staples
// (rice/biryani "serves 2") ~1 per 2.5 guests, ~1.5 breads a head,
// snacks/desserts ~1 pack per 5–6 guests.
const mainQty = (people) => Math.max(1, Math.round(people / 4.5))
const stapleQty = (guests) => Math.max(1, Math.round(guests / 2.5))
const packQty = (guests) => Math.max(1, Math.ceil(guests / 6))

function breadQty(guests, itemName) {
  const m = itemName.match(/\((\d+)\s*pcs?\)/)
  const perPack = m ? parseInt(m[1], 10) : 2
  return Math.max(1, Math.min(4, Math.ceil((guests * 1.5) / perPack)))
}

// ---------------------------------------------------------- composing

const notSpicy = (req) => (i) => !(req.avoid.includes('spicy') && i.spicy)
const vegOk = (req) => (i) => !(req.allVeg && !i.veg)

function toPlanItem(item, qty) {
  return {
    id: item.id,
    name: item.name,
    price: item.price,
    qty,
    veg: item.veg,
    emoji: item.emoji || '🍽️',
  }
}

function subtotalOf(items) {
  return items.reduce((a, x) => a + x.price * x.qty, 0)
}

// Score a restaurant the way agent.py's _dinner_course does: real main
// +30, role variety +10/role, menu depth, rating — plus dish-hint match.
function scoreRestaurant(r, menu, req) {
  const usable = menu.filter(notSpicy(req)).filter(vegOk(req))
  const roles = new Set(usable.map((i) => i.role))
  let score = 0
  if (roles.has('main')) score += 30
  score += roles.size * 10
  score += Math.min(usable.length, 10)
  score += r.rating * 4
  if (req.dishHints.some((h) => (r.dishesFor || []).includes(h))) score += 40
  if (req.allVeg && r.veg) score += 10
  return score
}

function composeDinner(req, share) {
  const candidates = restaurants
    .filter((r) => r.tags.includes('dinner'))
    .map((r) => ({ r, menu: getMenu(r.id) }))
    .filter((c) => c.menu.length > 0)
    .map((c) => ({ ...c, score: scoreRestaurant(c.r, c.menu, req) }))
    .sort((a, b) => b.score - a.score)

  const winner = candidates[0]
  const { r, menu } = winner
  const usable = menu.filter(notSpicy(req)).filter(vegOk(req))
  const byRole = (role) =>
    usable.filter((i) => i.role === role).sort((a, b) => (b.rating || 4) - (a.rating || 4))

  const items = []
  const seenNames = new Set() // real menus repeat names under new ids — dedupe by name
  const add = (item, qty) => {
    if (!item || seenNames.has(item.name) || qty < 1) return
    seenNames.add(item.name)
    items.push(toPlanItem(item, qty))
  }

  const vegPeople = req.allVeg ? req.guests : req.vegCount
  const nonvegPeople = req.guests - vegPeople

  // mains — one per dietary group, portions from headcount
  const mains = byRole('main')
  const vegMains = mains.filter((i) => i.veg)
  const nonvegMains = mains.filter((i) => !i.veg)
  if (vegPeople > 0 || nonvegMains.length === 0) {
    add(vegMains[0], mainQty(Math.max(vegPeople, nonvegMains.length ? vegPeople : req.guests)))
  }
  if (nonvegPeople > 0 && !req.allVeg) add(nonvegMains[0], mainQty(nonvegPeople))
  if (!items.length && mains.length) add(mains[0], mainQty(req.guests))

  // one staple (rice / biryani / noodles) — hinted dish wins if present;
  // an all-veg table gets a veg staple, a mixed table gets the best one
  // plus a veg staple so vegetarian guests aren't an afterthought
  const staples = byRole('staple')
  const hinted = staples.find((i) =>
    req.dishHints.some((h) => i.name.toLowerCase().includes(h)),
  )
  let staple = hinted
  if (!staple) {
    staple =
      req.allVeg || nonvegPeople === 0
        ? staples.find((i) => i.veg) || staples[0]
        : staples[0]
  }
  add(staple, stapleQty(nonvegPeople > 0 ? nonvegPeople : req.guests))
  if (staple && !staple.veg && vegPeople > 0) {
    add(
      staples.find((i) => i.veg && i.name !== staple.name),
      Math.max(1, Math.round(vegPeople / 2.5)),
    )
  }

  // bread
  const bread = byRole('bread')[0]
  if (bread) add(bread, breadQty(req.guests, bread.name))

  // fit the course budget: shrink quantities before dropping dishes
  let guard = 24
  while (subtotalOf(items) > share && guard-- > 0) {
    const reducible = [...items]
      .filter((x) => x.qty > 1)
      .sort((a, b) => b.price * b.qty - a.price * a.qty)[0]
    if (reducible) {
      reducible.qty -= 1
    } else if (items.length > 1) {
      const cheapestRole = items[items.length - 1]
      items.splice(items.indexOf(cheapestRole), 1)
    } else {
      break
    }
  }

  // top-up: spend a big leftover on variety — capped at 2 additions,
  // and never when the user named the dishes themselves
  if (!req.dishHints.length) {
    let additions = 0
    const sides = byRole('side')
    for (const side of sides) {
      if (additions >= 2) break
      if (seenNames.has(side.name)) continue
      const qty = Math.max(1, Math.round(req.guests / 4))
      if (subtotalOf(items) + side.price * qty <= share * 0.98) {
        add(side, qty)
        additions++
      }
    }
  }

  return {
    slot: 'dinner',
    platform: 'food',
    vendorName: r.name,
    vendorId: r.id,
    etaMin: TIMING.food.etaMin,
    bufferMin: TIMING.food.bufferMin,
    items,
    subtotal: subtotalOf(items),
    note: `Dinner from ${r.name} — best of ${Math.min(candidates.length, 4)} candidates checked (real mains, role variety, ${r.rating}★).`,
  }
}

function composeFromPool(slot, pool, req, share) {
  const usable = pool
    .filter((i) => !(req.avoid.includes('spicy') && i.tags.includes('spicy')))
    .filter((i) => !((req.vegCount > 0 || req.allVeg) && !i.veg))

  const items = []
  const qtyEach = packQty(req.guests)
  const maxDistinct = slot === 'snacks' ? 4 : 2

  for (const product of usable) {
    if (items.length >= maxDistinct) break
    const cost = product.price * qtyEach
    if (subtotalOf(items) + cost <= share) {
      items.push(toPlanItem(product, qtyEach))
    }
  }
  // always leave with at least the single most affordable thing
  if (!items.length && usable.length) {
    const cheapest = [...usable].sort((a, b) => a.price - b.price)[0]
    items.push(toPlanItem(cheapest, 1))
  }

  return {
    slot,
    platform: 'instamart',
    vendorName: 'Instamart',
    vendorId: null,
    etaMin: TIMING.instamart.etaMin,
    bufferMin: TIMING.instamart.bufferMin,
    items,
    subtotal: subtotalOf(items),
    note: null,
  }
}

// ---------------------------------------------------------- timing

function eatTimeFor(slot, req) {
  const anchor = req.eatAt
  const hasDinner = req.slots.includes('dinner')
  if (slot === 'dinner') return anchor
  if (slot === 'snacks') return hasDinner ? anchor - 60 : anchor
  return hasDinner ? anchor + 60 : anchor // dessert
}

// ---------------------------------------------------------- the plan

export function buildPlan(req) {
  const budget = req.budget ?? suggestBudget(req.guests, req.slots)
  const shares = budgetSplit(req.slots, budget)

  const courses = req.slots.map((slot) => {
    let course
    if (slot === 'dinner') course = composeDinner(req, shares[slot])
    else if (slot === 'snacks') course = composeFromPool('snacks', snackPool, req, shares[slot])
    else course = composeFromPool('dessert', dessertPool, req, shares[slot])

    const eatAt = eatTimeFor(slot, req)
    return {
      ...course,
      eatAt,
      orderAt: eatAt - (course.etaMin + course.bufferMin),
    }
  })

  const total = courses.reduce((a, c) => a + c.subtotal, 0)
  const notes = courses.filter((c) => c.note).map((c) => c.note)
  if (req.avoid.includes('spicy')) {
    notes.push('Skipped spicy dishes — matched against dish names, since Swiggy returns no "spicy" field.')
  }
  if (budget - total > 0) {
    notes.push(`₹${(budget - total).toLocaleString('en-IN')} left unspent — leftover stays honest rather than padding the cart.`)
  }

  return {
    id: `plan-${Date.now()}`,
    createdAt: new Date().toLocaleString('en-IN', {
      weekday: 'short', day: 'numeric', month: 'short',
      hour: 'numeric', minute: '2-digit',
    }),
    request: req.rawText,
    status: 'draft',
    guests: req.guests,
    budget,
    total,
    leftover: budget - total,
    assumptions: summariseAssumptions(req),
    notes,
    courses,
  }
}
