import { Clock, ShieldCheck, ShoppingBag, RotateCcw, Info } from 'lucide-react'
import { Button } from '../common/Button.jsx'
import { BudgetBar } from '../common/BudgetBar.jsx'
import { VegDot, PlatformBadge } from '../common/Primitives.jsx'
import { inr, fmtTime } from '../../utils/format.js'

const SLOT_META = {
  snacks: { emoji: '🥨', label: 'Snacks' },
  dinner: { emoji: '🍛', label: 'Dinner' },
  dessert: { emoji: '🍨', label: 'Dessert' },
}

function CourseCard({ course }) {
  const meta = SLOT_META[course.slot]
  return (
    <section className="course" aria-label={`${meta.label} course`}>
      <div className="course__node" aria-hidden="true">
        <span className="course__node-time">{fmtTime(course.orderAt)}</span>
        <span className="course__node-dot" />
      </div>
      <div className="course__card">
        <header className="course__head">
          <div className="course__title">
            <span className="course__emoji" aria-hidden="true">{meta.emoji}</span>
            <div>
              <h3 className="t-h3">{meta.label}</h3>
              <p className="t-sub">on the table at <strong>{fmtTime(course.eatAt)}</strong></p>
            </div>
          </div>
          <PlatformBadge platform={course.platform} />
        </header>

        <div className="course__timing">
          <Clock size={14} aria-hidden="true" />
          <span>
            Order at <strong>{fmtTime(course.orderAt)}</strong> · {course.etaMin} min delivery
            + {course.bufferMin} min buffer
          </span>
        </div>

        <p className="course__vendor">{course.vendorName}</p>

        <ul className="course__items">
          {course.items.map((item) => (
            <li key={item.id} className="course__item">
              <VegDot veg={item.veg} size={13} />
              <span className="course__item-qty">{item.qty} ×</span>
              <span className="course__item-name">{item.name}</span>
              <span className="course__item-price">{inr(item.price * item.qty)}</span>
            </li>
          ))}
        </ul>

        <div className="course__subtotal">
          <span>Subtotal</span>
          <span>{inr(course.subtotal)}</span>
        </div>
      </div>
    </section>
  )
}

export function PlanView({ plan, onApprove, onDiscard }) {
  return (
    <div className="planview anim-fade-up">
      {plan.assumptions.length > 0 && (
        <div className="planview__assumptions" role="note">
          <Info size={15} aria-hidden="true" />
          <div>
            <strong>Said out loud, not silently assumed: </strong>
            {plan.assumptions.join(' · ')}
          </div>
        </div>
      )}

      <div className="planview__timeline">
        {plan.courses.map((c) => (
          <CourseCard key={c.slot} course={c} />
        ))}
      </div>

      <div className="planview__budget">
        <BudgetBar spent={plan.total} budget={plan.budget} />
      </div>

      {plan.notes.length > 0 && (
        <ul className="planview__notes">
          {plan.notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      )}

      <div className="planview__actions">
        <Button size="lg" icon={ShoppingBag} onClick={onApprove}>
          Looks right — fill my carts
        </Button>
        <Button size="lg" variant="ghost" icon={RotateCcw} onClick={onDiscard}>
          Start over
        </Button>
      </div>

      <p className="planview__safety">
        <ShieldCheck size={15} aria-hidden="true" />
        Spread fills carts and stops. It never places an order or moves money —
        you check out in the Swiggy app, or don't.
      </p>
    </div>
  )
}
