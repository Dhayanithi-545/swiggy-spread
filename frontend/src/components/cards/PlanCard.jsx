import { Link } from 'react-router-dom'
import { Users, Wallet, ChevronRight } from 'lucide-react'
import { Badge } from '../common/Primitives.jsx'
import { inr, fmtTime } from '../../utils/format.js'
import { planStatusMeta } from '../../data/plans.js'

const SLOT_EMOJI = { snacks: '🥨', dinner: '🍛', dessert: '🍨' }

export function PlanCard({ plan }) {
  const status = planStatusMeta[plan.status] || planStatusMeta.draft

  return (
    <Link to={`/plans/${plan.id}`} className="plancard" aria-label={`Plan: ${plan.request}`}>
      <div className="plancard__head">
        <span className="t-caption">{plan.createdAt}</span>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>
      <p className="plancard__request">“{plan.request}”</p>
      <div className="plancard__courses">
        {plan.courses.map((c) => (
          <span key={c.slot} className="plancard__course">
            <span aria-hidden="true">{SLOT_EMOJI[c.slot]}</span>
            {c.slot} · {fmtTime(c.eatAt)}
          </span>
        ))}
      </div>
      <div className="plancard__foot">
        <span className="plancard__stat">
          <Users size={14} aria-hidden="true" /> {plan.guests} people
        </span>
        <span className="plancard__stat">
          <Wallet size={14} aria-hidden="true" /> {inr(plan.total)} of {inr(plan.budget)}
        </span>
        <ChevronRight size={17} className="plancard__chev" aria-hidden="true" />
      </div>
    </Link>
  )
}
