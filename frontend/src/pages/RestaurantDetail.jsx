import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ChevronRight, Clock, MapPin, Search, BadgePercent, ShoppingBag } from 'lucide-react'
import { FoodImage } from '../components/common/FoodImage.jsx'
import { RatingBadge, Chip } from '../components/common/Primitives.jsx'
import { DishRow } from '../components/cards/DishRow.jsx'
import { DishRowSkeleton } from '../components/common/Skeleton.jsx'
import { EmptyState } from '../components/common/States.jsx'
import { getRestaurant } from '../data/restaurants.js'
import { getMenu, menuCategories } from '../data/menus.js'
import { inr } from '../utils/format.js'
import { useFakeLoading } from '../hooks/useFakeLoading.js'
import { useCart } from '../context/CartContext.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

export default function RestaurantDetail() {
  const { id } = useParams()
  const restaurant = getRestaurant(id)
  useDocumentTitle(restaurant ? restaurant.name : 'Restaurant')
  const loading = useFakeLoading(600, id)

  const [vegFilter, setVegFilter] = useState(false)
  const [menuQuery, setMenuQuery] = useState('')
  const { cartFor } = useCart()

  const menu = useMemo(() => (restaurant ? getMenu(restaurant.id) : []), [restaurant])
  const cats = restaurant ? menuCategories(restaurant.id) : []

  if (!restaurant) {
    return (
      <div className="page container">
        <EmptyState
          emoji="🤷"
          title="We couldn't find that restaurant"
          message="It may have been a broken link — the kitchens nearby are still open."
          action="Browse restaurants"
          actionTo="/restaurants"
        />
      </div>
    )
  }

  const q = menuQuery.trim().toLowerCase()
  const visible = menu.filter(
    (dish) => (!vegFilter || dish.veg) && (!q || dish.name.toLowerCase().includes(q)),
  )
  const cart = cartFor('food', restaurant.id)
  const cartCount = cart?.items.reduce((a, x) => a + x.qty, 0) || 0
  const cartTotal = cart?.items.reduce((a, x) => a + x.price * x.qty, 0) || 0

  return (
    <div className="page container detailpage">
      <nav className="detailpage__crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={13} aria-hidden="true" />
        <Link to="/restaurants">Restaurants</Link>
        <ChevronRight size={13} aria-hidden="true" />
        <span aria-current="page">{restaurant.name}</span>
      </nav>

      <header className="detailpage__hero">
        <FoodImage
          emoji={restaurant.emoji}
          gradient={restaurant.gradient}
          name={restaurant.name}
          ratio="square"
          className="detailpage__img"
        />
        <div className="detailpage__info">
          <h1 className="t-h1">{restaurant.name}</h1>
          <p className="t-sub" style={{ marginTop: 4 }}>{restaurant.cuisines.join(', ')}</p>
          <div className="detailpage__stats">
            <RatingBadge rating={restaurant.rating} />
            <span className="t-sub">{restaurant.ratings} ratings</span>
            <span className="detailpage__dot" aria-hidden="true">·</span>
            <span className="t-sub"><Clock size={13} aria-hidden="true" /> {restaurant.etaMin}–{restaurant.etaMin + 5} mins</span>
            <span className="detailpage__dot" aria-hidden="true">·</span>
            <span className="t-sub">{inr(restaurant.costForTwo)} for two</span>
            <span className="detailpage__dot" aria-hidden="true">·</span>
            <span className="t-sub"><MapPin size={13} aria-hidden="true" /> {restaurant.area}, {restaurant.distanceKm} km</span>
          </div>
          {restaurant.offer && (
            <p className="detailpage__offer">
              <BadgePercent size={15} aria-hidden="true" />
              {restaurant.offer}
            </p>
          )}
        </div>
      </header>

      <div className="detailpage__menubar">
        <div className="detailpage__search">
          <Search size={15} aria-hidden="true" />
          <input
            value={menuQuery}
            onChange={(e) => setMenuQuery(e.target.value)}
            placeholder={`Search in ${restaurant.name}`}
            aria-label={`Search dishes in ${restaurant.name}`}
          />
        </div>
        <Chip active={vegFilter} onClick={() => setVegFilter(!vegFilter)}>
          <span className="vegdot vegdot--veg" style={{ width: 12, height: 12 }} aria-hidden="true"><i /></span>
          Veg only
        </Chip>
      </div>

      {loading ? (
        <div>
          {Array.from({ length: 5 }, (_, i) => <DishRowSkeleton key={i} />)}
        </div>
      ) : visible.length === 0 ? (
        <EmptyState
          emoji="🥣"
          title="No dishes match"
          message={vegFilter ? 'Nothing vegetarian matches that search here.' : 'Try a different dish name.'}
          action="Clear search"
          onAction={() => { setMenuQuery(''); setVegFilter(false) }}
        />
      ) : (
        <div className="detailpage__menu">
          {cats.map((cat) => {
            const dishes = visible.filter((x) => x.category === cat)
            if (!dishes.length) return null
            return (
              <section key={cat} aria-labelledby={`cat-${cat}`}>
                <h2 id={`cat-${cat}`} className="detailpage__cat">
                  {cat} <span className="t-sub">({dishes.length})</span>
                </h2>
                {dishes.map((dish) => (
                  <DishRow key={dish.id} dish={dish} restaurant={restaurant} />
                ))}
              </section>
            )
          })}
        </div>
      )}

      {cartCount > 0 && (
        <Link to="/carts" className="cartbar anim-fade-up" aria-label={`View cart, ${cartCount} items, ${inr(cartTotal)}`}>
          <span>{cartCount} item{cartCount > 1 ? 's' : ''} · {inr(cartTotal)}</span>
          <span className="cartbar__cta">
            View carts <ShoppingBag size={16} aria-hidden="true" />
          </span>
        </Link>
      )}
    </div>
  )
}
