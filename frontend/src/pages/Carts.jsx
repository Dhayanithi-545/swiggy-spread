import { useState } from 'react'
import { Clock, ExternalLink, ShieldCheck, Trash2 } from 'lucide-react'
import { Button } from '../components/common/Button.jsx'
import { Modal } from '../components/common/Modal.jsx'
import { BudgetBar } from '../components/common/BudgetBar.jsx'
import { VegDot, PlatformBadge, Badge } from '../components/common/Primitives.jsx'
import { QuantityStepper } from '../components/common/QuantityStepper.jsx'
import { EmptyState } from '../components/common/States.jsx'
import { useCart } from '../context/CartContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { inr, fmtTime } from '../utils/format.js'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

const SLOT_LABEL = { snacks: 'Snacks', dinner: 'Dinner', dessert: 'Dessert' }

function CartCard({ cart, onCheckout }) {
  const { setQty, removeCart } = useCart()
  const subtotal = cart.items.reduce((a, x) => a + x.price * x.qty, 0)
  const taxesEstimate = Math.round(subtotal * 0.1)

  return (
    <article className="cartcard anim-fade-up" aria-label={`${cart.vendorName} cart`}>
      <header className="cartcard__head">
        <div>
          <div className="cartcard__vendorrow">
            <h3 className="t-h3">{cart.vendorName}</h3>
            {cart.slot && <Badge tone="brand">{SLOT_LABEL[cart.slot]}</Badge>}
          </div>
          <PlatformBadge platform={cart.platform} />
        </div>
        <button
          type="button"
          className="cartcard__remove"
          onClick={() => removeCart(cart.id)}
          aria-label={`Remove ${cart.vendorName} cart`}
        >
          <Trash2 size={16} aria-hidden="true" />
        </button>
      </header>

      {cart.orderAt != null && (
        <p className="cartcard__timing">
          <Clock size={13} aria-hidden="true" />
          Order by <strong>{fmtTime(cart.orderAt)}</strong> to eat at{' '}
          <strong>{fmtTime(cart.eatAt)}</strong> ({cart.etaMin} min delivery)
        </p>
      )}

      <ul className="cartcard__items">
        {cart.items.map((item) => (
          <li key={item.id} className="cartcard__item">
            <span className="cartcard__item-emoji" aria-hidden="true">{item.emoji}</span>
            <span className="cartcard__item-name">
              <VegDot veg={item.veg} size={12} />
              {item.name}
            </span>
            <QuantityStepper
              size="sm"
              qty={item.qty}
              onInc={() => setQty(cart.id, item.id, item.qty + 1)}
              onDec={() => setQty(cart.id, item.id, item.qty - 1)}
            />
            <span className="cartcard__item-price">{inr(item.price * item.qty)}</span>
          </li>
        ))}
      </ul>

      <footer className="cartcard__foot">
        <div className="cartcard__totals">
          <span className="cartcard__subtotal">Items {inr(subtotal)}</span>
          <span className="t-caption">+ delivery & taxes ≈ {inr(taxesEstimate)} in the app</span>
        </div>
        <Button size="sm" variant="secondary" icon={ExternalLink} onClick={() => onCheckout(cart)}>
          Checkout in Swiggy
        </Button>
      </footer>
    </article>
  )
}

export default function Carts() {
  useDocumentTitle('My carts')
  const { carts, clearAll } = useCart()
  const toast = useToast()
  const [checkoutCart, setCheckoutCart] = useState(null)

  const planCarts = carts.filter((c) => c.fromPlan)
  const planBudget = planCarts[0]?.planBudget
  const planSpend = planCarts.reduce(
    (a, c) => a + c.items.reduce((b, x) => b + x.price * x.qty, 0),
    0,
  )

  return (
    <div className="page container cartspage">
      <header className="listpage__head cartspage__head">
        <div>
          <h1 className="t-h1">My carts</h1>
          <p className="t-sub">
            One cart per platform and restaurant — a gathering is several carts, on one clock.
          </p>
        </div>
        {carts.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            icon={Trash2}
            onClick={() => {
              clearAll()
              toast('All carts cleared', { type: 'info' })
            }}
          >
            Clear all
          </Button>
        )}
      </header>

      {carts.length === 0 ? (
        <EmptyState
          emoji="🛒"
          title="No carts yet"
          message="Plan an evening in one sentence, or browse a restaurant — everything you add lands here, grouped and timed."
          action="Plan an evening"
          actionTo="/plan"
        />
      ) : (
        <>
          {planBudget && (
            <div className="cartspage__budget">
              <BudgetBar spent={planSpend} budget={planBudget} />
            </div>
          )}

          <div className="cartspage__grid">
            {carts.map((cart) => (
              <CartCard key={cart.id} cart={cart} onCheckout={setCheckoutCart} />
            ))}
          </div>

          <p className="planview__safety" style={{ maxWidth: 640 }}>
            <ShieldCheck size={15} aria-hidden="true" />
            Spread filled these carts and stopped. Checkout, payment and coupons
            happen in the Swiggy app — enforced in code, not in a promise.
          </p>
        </>
      )}

      <Modal
        open={!!checkoutCart}
        onClose={() => setCheckoutCart(null)}
        title="This is where Spread stops"
      >
        <div className="checkout-modal">
          <p className="t-body">
            Your <strong>{checkoutCart?.vendorName}</strong> cart is filled and waiting
            inside the Swiggy app. Spread never places the order or touches payment —
            a cart is free and reversible, an order isn't.
          </p>
          <ol className="checkout-modal__steps">
            <li>Open the Swiggy app on your phone</li>
            <li>The cart is already filled — review it</li>
            <li>Apply any coupon you like, then pay and place the order yourself</li>
          </ol>
          <Button
            block
            onClick={() => {
              setCheckoutCart(null)
              toast('Handing over to you — the order is yours to place.', { type: 'safety' })
            }}
          >
            Got it
          </Button>
        </div>
      </Modal>
    </div>
  )
}
