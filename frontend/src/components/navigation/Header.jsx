import { useEffect, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import {
  ChevronDown, Search, Sparkles, BadgePercent, ShoppingBag, User, MapPin,
} from 'lucide-react'
import { useCart } from '../../context/CartContext.jsx'
import { LocationModal } from './LocationModal.jsx'
import { addresses } from '../../data/user.js'

export function Logo({ light = false }) {
  return (
    <Link to="/" className={`logo ${light ? 'logo--light' : ''}`} aria-label="Spread home">
      <span className="logo__mark" aria-hidden="true">
        <svg viewBox="0 0 64 64" width="30" height="30">
          <rect width="64" height="64" rx="16" fill="#fc8019" />
          <path d="M18 40c0-7.7 6.3-14 14-14s14 6.3 14 14" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round" />
          <circle cx="32" cy="19" r="4" fill="#fff" />
          <path d="M14 46h36" stroke="#fff" strokeWidth="5" strokeLinecap="round" />
        </svg>
      </span>
      <span className="logo__word">spread</span>
    </Link>
  )
}

export function Header() {
  const { itemCount } = useCart()
  const navigate = useNavigate()
  const [scrolled, setScrolled] = useState(false)
  const [locOpen, setLocOpen] = useState(false)
  const [address, setAddress] = useState(addresses[0])

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      <header className={`header ${scrolled ? 'header--scrolled' : ''}`}>
        <div className="container header__inner">
          <div className="header__left">
            <Logo />
            <button
              type="button"
              className="header__location"
              onClick={() => setLocOpen(true)}
              aria-label={`Delivery location: ${address.label}, ${address.area}. Change location`}
            >
              <MapPin size={15} className="header__location-pin" aria-hidden="true" />
              <span className="header__location-label">{address.label}</span>
              <span className="header__location-area">{address.area}</span>
              <ChevronDown size={15} className="header__location-caret" aria-hidden="true" />
            </button>
          </div>

          <button
            type="button"
            className="header__search"
            onClick={() => navigate('/search')}
            aria-label="Search for restaurants, dishes and groceries"
          >
            <Search size={16} aria-hidden="true" />
            <span>Search restaurants, dishes, groceries…</span>
          </button>

          <nav className="header__nav" aria-label="Primary">
            <NavLink to="/plan" className="header__link header__link--accent">
              <Sparkles size={17} aria-hidden="true" />
              <span>Plan an evening</span>
            </NavLink>
            <NavLink to="/offers" className="header__link">
              <BadgePercent size={17} aria-hidden="true" />
              <span>Offers</span>
            </NavLink>
            <NavLink to="/carts" className="header__link">
              <span className="header__cart-wrap">
                <ShoppingBag size={17} aria-hidden="true" />
                {itemCount > 0 && (
                  <span className="header__cart-badge" aria-label={`${itemCount} items in carts`}>
                    {itemCount > 99 ? '99+' : itemCount}
                  </span>
                )}
              </span>
              <span>Carts</span>
            </NavLink>
            <NavLink to="/profile" className="header__link">
              <User size={17} aria-hidden="true" />
              <span>Account</span>
            </NavLink>
          </nav>

          {/* mobile: search icon on the right; the rest lives in the bottom nav */}
          <button
            type="button"
            className="header__mobile-search"
            onClick={() => navigate('/search')}
            aria-label="Search"
          >
            <Search size={20} aria-hidden="true" />
          </button>
        </div>
      </header>

      <LocationModal
        open={locOpen}
        onClose={() => setLocOpen(false)}
        current={address}
        onSelect={(a) => {
          setAddress(a)
          setLocOpen(false)
        }}
      />
    </>
  )
}
