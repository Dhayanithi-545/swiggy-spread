import { useMemo, useState } from 'react'
import { SlidersHorizontal, Leaf, Star, Timer, Heart } from 'lucide-react'
import { Chip } from '../components/common/Primitives.jsx'
import { RestaurantCard } from '../components/cards/RestaurantCard.jsx'
import { GridSkeleton, RestaurantCardSkeleton } from '../components/common/Skeleton.jsx'
import { EmptyState } from '../components/common/States.jsx'
import { restaurants } from '../data/restaurants.js'
import { useFakeLoading } from '../hooks/useFakeLoading.js'
import { useFavorites } from '../context/FavoritesContext.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

const SORTS = [
  { id: 'relevance', label: 'Relevance' },
  { id: 'rating', label: 'Rating: high to low' },
  { id: 'eta', label: 'Delivery time' },
  { id: 'cost-asc', label: 'Cost: low to high' },
  { id: 'cost-desc', label: 'Cost: high to low' },
]

export default function Restaurants() {
  useDocumentTitle('Restaurants')
  const { favorites } = useFavorites()
  const [vegOnly, setVegOnly] = useState(false)
  const [topRated, setTopRated] = useState(false)
  const [fast, setFast] = useState(false)
  const [favOnly, setFavOnly] = useState(false)
  const [sort, setSort] = useState('relevance')

  const filterKey = `${vegOnly}|${topRated}|${fast}|${favOnly}|${sort}`
  const loading = useFakeLoading(550, filterKey)

  const list = useMemo(() => {
    let out = restaurants.filter(
      (r) =>
        (!vegOnly || r.veg) &&
        (!topRated || r.rating >= 4.2) &&
        (!fast || r.etaMin <= 35) &&
        (!favOnly || favorites.includes(r.id)),
    )
    if (sort === 'rating') out = [...out].sort((a, b) => b.rating - a.rating)
    if (sort === 'eta') out = [...out].sort((a, b) => a.etaMin - b.etaMin)
    if (sort === 'cost-asc') out = [...out].sort((a, b) => a.costForTwo - b.costForTwo)
    if (sort === 'cost-desc') out = [...out].sort((a, b) => b.costForTwo - a.costForTwo)
    return out
  }, [vegOnly, topRated, fast, favOnly, sort, favorites])

  const clearAll = () => {
    setVegOnly(false)
    setTopRated(false)
    setFast(false)
    setFavOnly(false)
    setSort('relevance')
  }

  return (
    <div className="page container listpage">
      <header className="listpage__head">
        <h1 className="t-h1">Restaurants near you</h1>
        <p className="t-sub">Pallavaram, Chennai · {restaurants.length} places delivering now</p>
      </header>

      <div className="listpage__filters" role="toolbar" aria-label="Filters and sorting">
        <label className="listpage__sort">
          <SlidersHorizontal size={14} aria-hidden="true" />
          <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort restaurants">
            {SORTS.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </label>
        <Chip icon={Leaf} active={vegOnly} onClick={() => setVegOnly(!vegOnly)}>Pure veg</Chip>
        <Chip icon={Star} active={topRated} onClick={() => setTopRated(!topRated)}>Rated 4.2+</Chip>
        <Chip icon={Timer} active={fast} onClick={() => setFast(!fast)}>Under 35 mins</Chip>
        <Chip icon={Heart} active={favOnly} onClick={() => setFavOnly(!favOnly)}>Favourites</Chip>
      </div>

      {loading ? (
        <GridSkeleton count={8} className="rgrid" Card={RestaurantCardSkeleton} />
      ) : list.length === 0 ? (
        <EmptyState
          emoji="🔍"
          title="Nothing matches those filters"
          message={favOnly && favorites.length === 0
            ? 'You haven’t favourited any places yet — tap the heart on a restaurant card.'
            : 'Loosen a filter or two and the kitchens come back.'}
          action="Clear all filters"
          onAction={clearAll}
        />
      ) : (
        <div className="rgrid anim-fade-up">
          {list.map((r) => (
            <RestaurantCard key={r.id} restaurant={r} />
          ))}
        </div>
      )}
    </div>
  )
}
