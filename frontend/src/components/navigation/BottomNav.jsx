import { NavLink } from 'react-router-dom'
import { Home, UtensilsCrossed, Sparkles, ShoppingBag, User } from 'lucide-react'
import { useCart } from '../../context/CartContext.jsx'

// Mobile-only bottom navigation. "Plan" sits raised in the middle —
// it's the product's signature action.
export function BottomNav() {
  const { itemCount } = useCart()

  const tab = ({ isActive }) => `bottomnav__tab ${isActive ? 'bottomnav__tab--active' : ''}`

  return (
    <nav className="bottomnav" aria-label="Primary mobile">
      <NavLink to="/" end className={tab}>
        <Home size={21} aria-hidden="true" />
        <span>Home</span>
      </NavLink>
      <NavLink to="/restaurants" className={tab}>
        <UtensilsCrossed size={21} aria-hidden="true" />
        <span>Food</span>
      </NavLink>
      <NavLink to="/plan" className="bottomnav__plan" aria-label="Plan an evening">
        <span className="bottomnav__plan-btn">
          <Sparkles size={22} aria-hidden="true" />
        </span>
        <span>Plan</span>
      </NavLink>
      <NavLink to="/carts" className={tab}>
        <span className="bottomnav__cart">
          <ShoppingBag size={21} aria-hidden="true" />
          {itemCount > 0 && <span className="bottomnav__badge">{itemCount > 99 ? '99+' : itemCount}</span>}
        </span>
        <span>Carts</span>
      </NavLink>
      <NavLink to="/profile" className={tab}>
        <User size={21} aria-hidden="true" />
        <span>Account</span>
      </NavLink>
    </nav>
  )
}
