import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search, X, Clock3, TrendingUp } from 'lucide-react'
import { RestaurantCard } from '../components/cards/RestaurantCard.jsx'
import { ProductCard } from '../components/cards/ProductCard.jsx'
import { VegDot } from '../components/common/Primitives.jsx'
import { FoodImage } from '../components/common/FoodImage.jsx'
import { EmptyState } from '../components/common/States.jsx'
import { restaurants, getRestaurant } from '../data/restaurants.js'
import { allDishes } from '../data/menus.js'
import { products } from '../data/instamart.js'
import { inr } from '../utils/format.js'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

const TRENDING = ['biryani', 'parotta', 'ice cream', 'pizza', 'chips', 'dosa']

export default function SearchPage() {
  useDocumentTitle('Search')
  const [params, setParams] = useSearchParams()
  const [text, setText] = useState(params.get('q') || '')
  const [recent, setRecent] = useLocalStorage('spread_recent_searches', [])
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // keep the input in sync when a category card navigates here
  useEffect(() => {
    setText(params.get('q') || '')
  }, [params])

  const q = text.trim().toLowerCase()

  const commit = (value) => {
    const v = value.trim()
    if (!v) return
    setParams({ q: v })
    setRecent((r) => [v, ...r.filter((x) => x !== v)].slice(0, 6))
  }

  const results = useMemo(() => {
    if (q.length < 2) return null
    const matchedRestaurants = restaurants.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        r.cuisines.some((c) => c.toLowerCase().includes(q)) ||
        (r.dishesFor || []).some((dd) => dd.includes(q)),
    )
    const dishes = allDishes
      .filter((dd) => dd.name.toLowerCase().includes(q))
      .slice(0, 8)
    const groceries = products.filter((p) => p.name.toLowerCase().includes(q))
    return { matchedRestaurants, dishes, groceries }
  }, [q])

  const empty =
    results &&
    results.matchedRestaurants.length === 0 &&
    results.dishes.length === 0 &&
    results.groceries.length === 0

  return (
    <div className="page container searchpage">
      <form
        className="searchpage__box"
        onSubmit={(e) => {
          e.preventDefault()
          commit(text)
        }}
        role="search"
      >
        <Search size={18} aria-hidden="true" />
        <input
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Search restaurants, dishes, groceries…"
          aria-label="Search restaurants, dishes and groceries"
        />
        {text && (
          <button type="button" onClick={() => { setText(''); setParams({}) }} aria-label="Clear search">
            <X size={17} aria-hidden="true" />
          </button>
        )}
      </form>

      {!results && (
        <div className="searchpage__idle anim-fade-up">
          {recent.length > 0 && (
            <section aria-labelledby="recent-h">
              <h2 id="recent-h" className="t-label searchpage__label">
                <Clock3 size={13} aria-hidden="true" /> Recent searches
              </h2>
              <div className="searchpage__chips">
                {recent.map((r) => (
                  <button key={r} type="button" className="chip" onClick={() => commit(r)}>{r}</button>
                ))}
              </div>
            </section>
          )}
          <section aria-labelledby="trend-h">
            <h2 id="trend-h" className="t-label searchpage__label">
              <TrendingUp size={13} aria-hidden="true" /> Trending around you
            </h2>
            <div className="searchpage__chips">
              {TRENDING.map((t) => (
                <button key={t} type="button" className="chip" onClick={() => commit(t)}>{t}</button>
              ))}
            </div>
          </section>
        </div>
      )}

      {results && empty && (
        <EmptyState
          emoji="🫙"
          title={`Nothing found for “${text}”`}
          message="Check the spelling, or try a dish, a cuisine or a grocery item."
          action="Browse restaurants instead"
          actionTo="/restaurants"
        />
      )}

      {results && !empty && (
        <div className="searchpage__results anim-fade-up">
          {results.dishes.length > 0 && (
            <section aria-labelledby="dishes-h">
              <h2 id="dishes-h" className="t-h2 searchpage__section">Dishes</h2>
              <p className="t-caption" style={{ marginTop: -4, marginBottom: 12 }}>
                One search, every restaurant — this is what the planner's dish hints use.
              </p>
              <ul className="searchpage__dishlist">
                {results.dishes.map((dish) => {
                  const r = getRestaurant(dish.restaurantId)
                  return (
                    <li key={`${dish.restaurantId}-${dish.id}`}>
                      <Link to={`/restaurants/${dish.restaurantId}`} className="searchpage__dish">
                        <FoodImage emoji={dish.emoji} name={dish.name} size={52} ratio="square" />
                        <span className="searchpage__dish-main">
                          <span className="searchpage__dish-name">
                            <VegDot veg={dish.veg} size={12} /> {dish.name}
                          </span>
                          <span className="t-caption">{r?.name} · {r?.area}</span>
                        </span>
                        <span className="searchpage__dish-price">{inr(dish.price)}</span>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </section>
          )}

          {results.matchedRestaurants.length > 0 && (
            <section aria-labelledby="rest-h">
              <h2 id="rest-h" className="t-h2 searchpage__section">Restaurants</h2>
              <div className="rgrid">
                {results.matchedRestaurants.map((r) => (
                  <RestaurantCard key={r.id} restaurant={r} />
                ))}
              </div>
            </section>
          )}

          {results.groceries.length > 0 && (
            <section aria-labelledby="groc-h">
              <h2 id="groc-h" className="t-h2 searchpage__section">On Instamart</h2>
              <div className="pgrid">
                {results.groceries.map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
