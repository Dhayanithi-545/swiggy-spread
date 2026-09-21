# Spread — frontend

The web UI for **Spread**: you say *"6 friends Saturday 8pm, budget 3000,
2 are vegetarian"* and it plans the whole gathering across Swiggy Food +
Instamart — timed carts, one budget, and **it never places an order**.

## Run it

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173.

**Frontend only.** No backend calls, no APIs, no auth — every screen runs on
realistic mock data (`src/data/`) and a client-side port of the backend's
planner logic (`src/utils/planner.js`). Carts, favorites, plans and recent
searches persist to `localStorage` so the app behaves like a working product.

## The flow worth demoing

1. Home → type (or click) *"6 friends coming over Saturday, sort it out"*
2. The clarify chat asks only what changes the outcome (courses → guests →
   time → budget), max 3 questions, each with a default answer.
3. The plan appears as a timeline: order times worked backwards from when
   food should land, portions composed as a spread (main + rice + bread),
   one budget bar held across all courses.
4. "Fill my carts" → `/carts` shows one timed cart per course. Checkout is a
   hand-off: Spread stops where money starts.

## Pages

| Route | What it is |
| --- | --- |
| `/` | Hero with the natural-language input, categories, top restaurants, Instamart strip |
| `/plan` | The clarify chat → planning loader → plan timeline |
| `/restaurants`, `/restaurants/:id` | Listing with filters/sort; menu with veg filter, search-in-menu, add-to-cart |
| `/instamart` | Quick-commerce grid with category tabs |
| `/search` | Recent + trending, results grouped into dishes / restaurants / Instamart |
| `/carts` | Multi-cart view with per-cart timing and the budget bar |
| `/plans`, `/plans/:id` | Plan history and a re-openable plan timeline |
| `/offers` | Read-only coupons (matching the backend's real stance) |
| `/profile` | Account, addresses, planning preferences, the safety rule |

## Structure

```
src/
  components/   common atoms, cards, navigation, home sections, plan flow
  context/      carts (multi-cart), toasts, favorites
  data/         mock restaurants, menus, instamart, offers, plans, user
  hooks/        localStorage, fake loading, media query, document title
  layouts/      MainLayout (header + bottom nav + footer)
  pages/        one file per route, lazy-loaded
  routes/       router with Suspense fallback
  styles/       tokens (design system) + per-area stylesheets
  utils/        formatting + the planner port
```

## Design system

Everything hangs off CSS custom properties in `src/styles/tokens.css`:
Swiggy-family orange (`#fc8019`), a 4-step ink scale, one shadow ramp, one
radius ramp, Inter for type. Food imagery is deterministic gradient + emoji
tiles (`FoodImage`) — no proprietary assets.

## Deliberately not here

- No calls to `backend/` — the backend stays untouched.
- No checkout, payment, or order placement anywhere in the UI. The backend
  enforces this in code; the frontend mirrors it in design.
