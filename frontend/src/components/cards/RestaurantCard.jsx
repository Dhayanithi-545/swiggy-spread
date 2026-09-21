import { Link } from 'react-router-dom'
import { Heart, Clock, MapPin } from 'lucide-react'
import { FoodImage } from '../common/FoodImage.jsx'
import { RatingBadge } from '../common/Primitives.jsx'
import { inr } from '../../utils/format.js'
import { useFavorites } from '../../context/FavoritesContext.jsx'

export function RestaurantCard({ restaurant, compact = false }) {
  const { isFavorite, toggleFavorite } = useFavorites()
  const fav = isFavorite(restaurant.id)

  return (
    <Link
      to={`/restaurants/${restaurant.id}`}
      className={`rcard ${compact ? 'rcard--compact' : ''}`}
      aria-label={`${restaurant.name}, ${restaurant.cuisines.join(', ')}, rated ${restaurant.rating}`}
    >
      <div className="rcard__media">
        <FoodImage
          emoji={restaurant.emoji}
          gradient={restaurant.gradient}
          name={restaurant.name}
          ratio="wide"
        />
        {restaurant.offer && <span className="rcard__offer">{restaurant.offer}</span>}
        {restaurant.promoted && <span className="rcard__promoted">Promoted</span>}
        <button
          type="button"
          className={`rcard__fav ${fav ? 'rcard__fav--on' : ''}`}
          onClick={(e) => {
            e.preventDefault()
            toggleFavorite(restaurant.id)
          }}
          aria-label={fav ? `Remove ${restaurant.name} from favourites` : `Add ${restaurant.name} to favourites`}
          aria-pressed={fav}
        >
          <Heart size={16} fill={fav ? 'currentColor' : 'none'} aria-hidden="true" />
        </button>
      </div>

      <div className="rcard__body">
        <div className="rcard__toprow">
          <h3 className="rcard__name">{restaurant.name}</h3>
          <RatingBadge rating={restaurant.rating} />
        </div>
        <p className="rcard__cuisines">{restaurant.cuisines.join(', ')}</p>
        <div className="rcard__meta">
          <span>
            <Clock size={13} aria-hidden="true" />
            {restaurant.etaMin}–{restaurant.etaMin + 5} mins
          </span>
          <span className="rcard__dot" aria-hidden="true">·</span>
          <span>{inr(restaurant.costForTwo)} for two</span>
          <span className="rcard__dot" aria-hidden="true">·</span>
          <span>
            <MapPin size={13} aria-hidden="true" />
            {restaurant.area}
          </span>
        </div>
      </div>
    </Link>
  )
}
