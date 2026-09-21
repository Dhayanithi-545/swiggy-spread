import { MessageCircleQuestion, CalendarClock, Wallet, ShieldCheck } from 'lucide-react'

const STEPS = [
  {
    icon: MessageCircleQuestion,
    title: 'It asks, never assumes',
    body: 'Courses come from you. When your request is ambiguous, Spread asks — at most 3 questions, each with a default you can just accept.',
  },
  {
    icon: CalendarClock,
    title: 'Timed backwards',
    body: 'Eat at 8? Dinner orders at 7:02 — 38 minutes of delivery plus a 20-minute buffer. Snacks ride a faster platform, so they start later.',
  },
  {
    icon: Wallet,
    title: 'One budget, every cart',
    body: 'The budget survives across snacks, dinner and dessert carts. Leftover money stays unspent — honest beats absurd.',
  },
  {
    icon: ShieldCheck,
    title: 'Carts, never orders',
    body: 'Spread fills your Swiggy carts and stops. Placing the order and paying is always yours, enforced in code at two layers.',
  },
]

export function HowItWorks() {
  return (
    <section className="how container" aria-labelledby="how-title">
      <h2 id="how-title" className="t-h1 how__title">Why this beats “an AI that orders food”</h2>
      <p className="t-sub how__sub">
        Any assistant can fill one cart, one moment. A gathering is three carts,
        two platforms and a clock.
      </p>
      <div className="how__grid">
        {STEPS.map((s, i) => (
          <article key={s.title} className="how__step" style={{ animationDelay: `${i * 60}ms` }}>
            <span className="how__icon">
              <s.icon size={21} aria-hidden="true" />
            </span>
            <h3 className="t-h3">{s.title}</h3>
            <p className="t-sub">{s.body}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
