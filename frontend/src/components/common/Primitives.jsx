import { Star, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

// Small shared atoms. Anything three pages use lives here.

export function Badge({ tone = 'neutral', children }) {
  return <span className={`badge badge--${tone}`}>{children}</span>
}

export function Chip({ active = false, onClick, children, icon: Icon }) {
  return (
    <button
      type="button"
      className={`chip ${active ? 'chip--active' : ''}`}
      onClick={onClick}
      aria-pressed={active}
    >
      {Icon && <Icon size={14} aria-hidden="true" />}
      {children}
    </button>
  )
}

// The little square that marks veg (green) / non-veg (red) — an Indian
// food-app convention users scan for before anything else.
export function VegDot({ veg, size = 14 }) {
  return (
    <span
      className={`vegdot ${veg ? 'vegdot--veg' : 'vegdot--nonveg'}`}
      style={{ width: size, height: size }}
      role="img"
      aria-label={veg ? 'Vegetarian' : 'Non-vegetarian'}
    >
      <i />
    </span>
  )
}

export function RatingBadge({ rating, muted = false }) {
  if (!rating) return null
  const low = rating < 4.0
  return (
    <span className={`rating ${low ? 'rating--low' : ''} ${muted ? 'rating--muted' : ''}`}>
      <Star size={11} fill="currentColor" aria-hidden="true" />
      {rating.toFixed(1)}
    </span>
  )
}

export function SectionHeader({ title, subtitle, to, linkLabel = 'See all' }) {
  return (
    <div className="section-header">
      <div>
        <h2 className="t-h2">{title}</h2>
        {subtitle && <p className="t-sub" style={{ marginTop: 2 }}>{subtitle}</p>}
      </div>
      {to && (
        <Link to={to} className="section-header__link">
          {linkLabel}
          <ArrowRight size={15} aria-hidden="true" />
        </Link>
      )}
    </div>
  )
}

export function PlatformBadge({ platform }) {
  const isIm = platform === 'instamart'
  return (
    <span className={`platform-badge ${isIm ? 'platform-badge--im' : 'platform-badge--food'}`}>
      {isIm ? '⚡ Instamart' : '🛵 Swiggy Food'}
    </span>
  )
}
