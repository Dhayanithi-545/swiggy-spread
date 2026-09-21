import { inr } from '../../utils/format.js'

// The budget, held visibly. Green while under, amber near the line,
// red past it — the single constraint the whole product exists to keep.
export function BudgetBar({ spent, budget, compact = false }) {
  const pct = Math.min(100, (spent / budget) * 100)
  const tone = spent > budget ? 'over' : pct > 92 ? 'near' : 'ok'
  const leftover = budget - spent

  return (
    <div className={`budgetbar ${compact ? 'budgetbar--compact' : ''}`}>
      <div className="budgetbar__row">
        <span className="t-label">Budget held across carts</span>
        <span className={`budgetbar__nums budgetbar__nums--${tone}`}>
          {inr(spent)} <span className="t-caption">of {inr(budget)}</span>
        </span>
      </div>
      <div
        className="budgetbar__track"
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${inr(spent)} of ${inr(budget)} budget used`}
      >
        <div className={`budgetbar__fill budgetbar__fill--${tone}`} style={{ width: `${pct}%` }} />
      </div>
      {!compact && (
        <p className="t-caption" style={{ marginTop: 6 }}>
          {leftover >= 0
            ? `${inr(leftover)} left over — unspent stays honest.`
            : `${inr(-leftover)} over — the planner would rebalance this.`}
        </p>
      )}
    </div>
  )
}
