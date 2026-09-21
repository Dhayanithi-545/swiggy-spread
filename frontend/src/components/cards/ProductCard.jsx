import { Zap } from 'lucide-react'
import { FoodImage } from '../common/FoodImage.jsx'
import { VegDot } from '../common/Primitives.jsx'
import { QuantityStepper } from '../common/QuantityStepper.jsx'
import { inr } from '../../utils/format.js'
import { useCart } from '../../context/CartContext.jsx'
import { useToast } from '../../context/ToastContext.jsx'

// Instamart product tile — quick-commerce styling: compact, price +
// strikethrough MRP, instant ETA flash.
export function ProductCard({ product }) {
  const { cartFor, addItem, setQty } = useCart()
  const toast = useToast()

  const cart = cartFor('instamart', null)
  const line = cart?.items.find((x) => x.id === product.id)
  const qty = line?.qty || 0
  const off = Math.round(((product.mrp - product.price) / product.mrp) * 100)

  return (
    <article className="pcard">
      <div className="pcard__media">
        <FoodImage emoji={product.emoji} name={product.name} ratio="square" />
        {off >= 10 && <span className="pcard__off">{off}% OFF</span>}
      </div>
      <div className="pcard__eta">
        <Zap size={11} fill="currentColor" aria-hidden="true" />
        {product.etaMin} mins
      </div>
      <div className="pcard__namerow">
        <VegDot veg={product.veg} size={12} />
        <h4 className="pcard__name">{product.name}</h4>
      </div>
      <p className="pcard__qty">{product.qty}</p>
      <div className="pcard__bottom">
        <div className="pcard__prices">
          <span className="pcard__price">{inr(product.price)}</span>
          {product.mrp > product.price && <s className="pcard__mrp">{inr(product.mrp)}</s>}
        </div>
        <QuantityStepper
          size="sm"
          qty={qty}
          onAdd={() => {
            addItem({ platform: 'instamart', vendorId: null, vendorName: 'Instamart', etaMin: 15 }, product)
            toast('Added to your Instamart cart')
          }}
          onInc={() => setQty(cart.id, product.id, qty + 1)}
          onDec={() => setQty(cart.id, product.id, qty - 1)}
        />
      </div>
    </article>
  )
}
