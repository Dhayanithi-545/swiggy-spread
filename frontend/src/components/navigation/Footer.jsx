import { Link } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { Logo } from './Header.jsx'

export function Footer() {
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <div className="footer__brand">
          <Logo light />
          <p className="footer__tag">
            One sentence. The whole evening, sorted — snacks, dinner and dessert
            timed to land together, on one budget.
          </p>
          <div className="footer__safety">
            <ShieldCheck size={16} aria-hidden="true" />
            <span>Fills your carts. Never places an order. Never moves money.</span>
          </div>
        </div>

        <nav className="footer__col" aria-label="Product">
          <h4 className="t-label">Product</h4>
          <Link to="/plan">Plan an evening</Link>
          <Link to="/restaurants">Restaurants</Link>
          <Link to="/instamart">Instamart</Link>
          <Link to="/offers">Offers</Link>
        </nav>

        <nav className="footer__col" aria-label="You">
          <h4 className="t-label">You</h4>
          <Link to="/plans">My plans</Link>
          <Link to="/carts">My carts</Link>
          <Link to="/profile">Account</Link>
          <Link to="/search">Search</Link>
        </nav>

        <div className="footer__col" aria-label="About">
          <h4 className="t-label">About</h4>
          <span className="footer__muted">Built on Swiggy's public MCP platform</span>
          <span className="footer__muted">Not affiliated with Swiggy</span>
          <span className="footer__muted">Frontend demo — mock data only</span>
        </div>
      </div>
      <div className="container footer__bottom">
        <span>© 2026 Spread. A planning agent, not a payment agent.</span>
      </div>
    </footer>
  )
}
