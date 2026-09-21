import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight, ShieldCheck } from 'lucide-react'

const EXAMPLES = [
  '6 friends Saturday 8pm, budget 3000, 2 are veg',
  'order dinner for 4 tonight',
  'snacks for the match, we are 8',
  'need a cake and ice cream for 8pm',
]

// The hero IS the product: one sentence in, a planned evening out.
export function Hero() {
  const navigate = useNavigate()
  const [text, setText] = useState('')

  const go = (q) => navigate(`/plan?q=${encodeURIComponent(q)}`)

  return (
    <section className="hero">
      <div className="hero__glow" aria-hidden="true" />
      <div className="container hero__inner">
        <div className="hero__copy">
          <span className="hero__eyebrow">
            <Sparkles size={14} aria-hidden="true" />
            A planning agent, not another menu
          </span>
          <h1 className="t-display hero__title">
            One sentence.
            <br />
            The whole evening, <em>sorted</em>.
          </h1>
          <p className="hero__sub">
            Spread plans snacks, dinner and dessert across Swiggy Food and
            Instamart, times every order backwards so food lands when you want
            it, and holds one budget across all your carts.
          </p>

          <form
            className="hero__form"
            onSubmit={(e) => {
              e.preventDefault()
              if (text.trim()) go(text.trim())
            }}
          >
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Try: 6 friends Saturday 8pm, budget 3000, 2 are veg"
              aria-label="Describe your gathering"
            />
            <button type="submit" className="hero__go" disabled={!text.trim()}>
              <span>Plan it</span>
              <ArrowRight size={17} aria-hidden="true" />
            </button>
          </form>

          <div className="hero__examples" aria-label="Example requests">
            {EXAMPLES.map((ex) => (
              <button key={ex} type="button" className="hero__example" onClick={() => go(ex)}>
                “{ex}”
              </button>
            ))}
          </div>

          <p className="hero__safety">
            <ShieldCheck size={14} aria-hidden="true" />
            Fills your carts — never places an order, never moves money.
          </p>
        </div>

        <div className="hero__preview" aria-hidden="true">
          <div className="hero__ticket hero__ticket--1">
            <span className="hero__ticket-time">6:30 PM</span>
            <span className="hero__ticket-emoji">🥨</span>
            <div>
              <strong>Snacks</strong>
              <span>Instamart · 15 min</span>
            </div>
            <span className="hero__ticket-amt">₹540</span>
          </div>
          <div className="hero__ticket hero__ticket--2">
            <span className="hero__ticket-time">7:02 PM</span>
            <span className="hero__ticket-emoji">🍛</span>
            <div>
              <strong>Dinner</strong>
              <span>Vasantha Aavaram · 38 min</span>
            </div>
            <span className="hero__ticket-amt">₹1,680</span>
          </div>
          <div className="hero__ticket hero__ticket--3">
            <span className="hero__ticket-time">8:30 PM</span>
            <span className="hero__ticket-emoji">🍨</span>
            <div>
              <strong>Dessert</strong>
              <span>Instamart · 15 min</span>
            </div>
            <span className="hero__ticket-amt">₹580</span>
          </div>
          <div className="hero__budget-pill">₹2,800 of ₹3,000 · ₹200 left over</div>
        </div>
      </div>
    </section>
  )
}
