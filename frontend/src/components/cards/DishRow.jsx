import { Flame, Star } from 'lucide-react'
import { FoodImage } from '../common/FoodImage.jsx'
import { VegDot } from '../common/Primitives.jsx'
import { QuantityStepper } from '../common/QuantityStepper.jsx'
import { inr } from '../../utils/format.js'
import { useCart } from '../../context/CartContext.jsx'
import { useToast } from '../../context/ToastContext.jsx'

// One dish on a restaurant menu — text block left, image + ADD right,
// the layout every Indian food app trains your thumb on.
export function DishRow({ dish, restaurant }) {
  const { cartFor, addItem, setQty } = useCart()
  const toast = useToast()

  const cart = cartFor('food', restaurant.id)
  const line = cart?.items.find((x) => x.id === dish.id)
  const qty = line?.qty || 0

  const source = {
    platform: 'food',
    vendorId: restaurant.id,
    vendorName: restaurant.name,
    etaMin: restaurant.etaMin,
  }

  return (
    <article className="dishrow">
      <div className="dishrow__info">
        <div className="dishrow__flags">
          <VegDot veg={dish.veg} />
          {dish.bestseller && (
            <span className="dishrow__bestseller">
              <Star size={11} fill="currentColor" aria-hidden="true" /> Bestseller
            </span>
          )}
          {dish.spicy && (
            <span className="dishrow__spicy" title="Spicy">
              <Flame size={12} aria-hidden="true" /> Spicy
            </span>
          )}
        </div>
        <h4 className="dishrow__name">{dish.name}</h4>
        <div className="dishrow__price">{inr(dish.price)}</div>
        {dish.rating && (
          <div className="dishrow__rating">
            <Star size={12} fill="currentColor" aria-hidden="true" />
            {dish.rating.toFixed(1)}
            <span>({dish.votes})</span>
          </div>
        )}
        {dish.description && <p className="dishrow__desc">{dish.description}</p>}
      </div>

      <div className="dishrow__media">
        <FoodImage emoji={dish.emoji} name={dish.name} ratio="square" className="dishrow__img" />
        <div className="dishrow__stepper">
          <QuantityStepper
            qty={qty}
            onAdd={() => {
              addItem(source, dish)
              toast(`Added to your ${restaurant.name} cart`)
            }}
            onInc={() => setQty(cart.id, dish.id, qty + 1)}
            onDec={() => setQty(cart.id, dish.id, qty - 1)}
          />
        </div>
      </div>
    </article>
  )
}
