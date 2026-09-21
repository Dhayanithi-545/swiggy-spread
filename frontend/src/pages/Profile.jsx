import { useState } from 'react'
import {
  MapPin, Briefcase, Home as HomeIcon, ShieldCheck, LogOut, ChevronRight,
  Leaf, Flame, Users, Wallet,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '../components/common/Primitives.jsx'
import { Button } from '../components/common/Button.jsx'
import { user, addresses, defaultPreferences } from '../data/user.js'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { useToast } from '../context/ToastContext.jsx'
import { useCart } from '../context/CartContext.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

const LABEL_ICONS = { Home: HomeIcon, Work: Briefcase }

function Toggle({ checked, onChange, label, icon: Icon, hint }) {
  return (
    <label className="pref-toggle">
      <span className="pref-toggle__icon"><Icon size={17} aria-hidden="true" /></span>
      <span className="pref-toggle__text">
        <span className="pref-toggle__label">{label}</span>
        {hint && <span className="t-caption">{hint}</span>}
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        role="switch"
        aria-checked={checked}
      />
      <span className="pref-toggle__track" aria-hidden="true"><i /></span>
    </label>
  )
}

export default function Profile() {
  useDocumentTitle('Account')
  const [prefs, setPrefs] = useLocalStorage('spread_prefs', defaultPreferences)
  const { savedPlans, carts } = useCart()
  const toast = useToast()
  const [signedOut, setSignedOut] = useState(false)

  const initials = user.name.split(' ').map((w) => w[0]).join('').slice(0, 2)

  return (
    <div className="page container profilepage">
      <header className="profilepage__card">
        <span className="profilepage__avatar" aria-hidden="true">{initials}</span>
        <div className="profilepage__who">
          <h1 className="t-h2">{user.name}</h1>
          <p className="t-sub">{user.phone} · {user.email}</p>
          <p className="t-caption">Planning evenings since {user.memberSince}</p>
        </div>
        <div className="profilepage__stats">
          <Link to="/plans" className="profilepage__stat">
            <strong>{savedPlans.length + 3}</strong>
            <span>plans</span>
          </Link>
          <Link to="/carts" className="profilepage__stat">
            <strong>{carts.length}</strong>
            <span>open carts</span>
          </Link>
        </div>
      </header>

      <div className="profilepage__cols">
        <section className="profilepage__panel" aria-labelledby="addr-h">
          <h2 id="addr-h" className="t-h3">Saved addresses</h2>
          <ul className="loc-list" style={{ marginTop: 14 }}>
            {addresses.map((a) => {
              const Icon = LABEL_ICONS[a.label] || MapPin
              return (
                <li key={a.id}>
                  <div className="loc-item" style={{ cursor: 'default' }}>
                    <span className="loc-item__icon"><Icon size={17} aria-hidden="true" /></span>
                    <span className="loc-item__body">
                      <span className="loc-item__label">
                        {a.label}
                        {a.isDefault && <span className="badge badge--brand">Default</span>}
                      </span>
                      <span className="t-sub">{a.line}, {a.area} — {a.pincode}</span>
                    </span>
                  </div>
                </li>
              )
            })}
          </ul>
          <p className="t-caption" style={{ marginTop: 10 }}>
            Live mode reads addresses from your Swiggy account after a one-time login.
          </p>
        </section>

        <section className="profilepage__panel" aria-labelledby="pref-h">
          <h2 id="pref-h" className="t-h3">Planning preferences</h2>
          <div className="profilepage__prefs">
            <Toggle
              icon={Leaf}
              label="Default to vegetarian"
              hint="New plans start veg-only unless you say otherwise"
              checked={prefs.vegOnly}
              onChange={(v) => setPrefs({ ...prefs, vegOnly: v })}
            />
            <Toggle
              icon={Flame}
              label="Avoid spicy dishes"
              hint="Matched against dish names — Swiggy has no spice field"
              checked={prefs.avoidSpice}
              onChange={(v) => setPrefs({ ...prefs, avoidSpice: v })}
            />
            <div className="pref-row">
              <span className="pref-toggle__icon"><Users size={17} aria-hidden="true" /></span>
              <span className="pref-toggle__text">
                <span className="pref-toggle__label">Usual headcount</span>
                <span className="t-caption">The default when a request doesn't say</span>
              </span>
              <select
                value={prefs.defaultGuests}
                onChange={(e) => setPrefs({ ...prefs, defaultGuests: Number(e.target.value) })}
                aria-label="Usual headcount"
              >
                {[2, 4, 6, 8, 10].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div className="pref-row">
              <span className="pref-toggle__icon"><Wallet size={17} aria-hidden="true" /></span>
              <span className="pref-toggle__text">
                <span className="pref-toggle__label">Comfort budget per head</span>
                <span className="t-caption">Used to suggest a range, never to decide</span>
              </span>
              <select
                value={prefs.defaultBudgetPerHead}
                onChange={(e) => setPrefs({ ...prefs, defaultBudgetPerHead: Number(e.target.value) })}
                aria-label="Comfort budget per head"
              >
                {[200, 250, 300, 400].map((n) => <option key={n} value={n}>₹{n}</option>)}
              </select>
            </div>
          </div>
        </section>
      </div>

      <section className="profilepage__safety" aria-labelledby="safety-h">
        <ShieldCheck size={22} aria-hidden="true" />
        <div>
          <h2 id="safety-h" className="t-h3">The rule above everything</h2>
          <p className="t-sub" style={{ marginTop: 6 }}>
            Spread can never place an order or move money — not by flag, not by
            setting, not by an agent deciding it would be helpful. It's enforced at
            two independent layers in code: the typed order calls refuse, and every
            single tool call is checked against a deny-list before it reaches the
            wire. There is no switch on this page because there is no switch at all.
          </p>
        </div>
      </section>

      <div className="profilepage__signout">
        {signedOut ? (
          <Badge tone="neutral">Signed out (pretend) — refresh to sign back in</Badge>
        ) : (
          <Button
            variant="ghost"
            icon={LogOut}
            onClick={() => {
              setSignedOut(true)
              toast('Signed out — mock only, nothing to revoke.', { type: 'info' })
            }}
          >
            Sign out
          </Button>
        )}
        <Link to="/plans" className="section-header__link">
          My plans <ChevronRight size={15} aria-hidden="true" />
        </Link>
      </div>
    </div>
  )
}
