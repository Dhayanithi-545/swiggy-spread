import { hashCode } from '../../utils/format.js'

// Food imagery without proprietary assets: a warm gradient tile with a
// large emoji, deterministic per name so the same dish always looks the
// same. Ratios: square | wide | tall.
const GRADIENTS = ['g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7', 'g8', 'g9', 'g10']

export function FoodImage({ emoji, name = '', gradient, ratio = 'square', size, className = '' }) {
  const g = gradient || GRADIENTS[hashCode(name || emoji || 'x') % GRADIENTS.length]
  const style = size ? { width: size, height: size, fontSize: size * 0.46 } : undefined
  return (
    <div
      className={`food-img food-img--${ratio} grad-${g} ${className}`}
      style={style}
      role="img"
      aria-label={name || 'Food'}
    >
      <span className="food-img__emoji" aria-hidden="true">
        {emoji || '🍽️'}
      </span>
      <span className="food-img__shine" aria-hidden="true" />
    </div>
  )
}
