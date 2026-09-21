import { useEffect, useState } from 'react'
import { Bone } from '../common/Skeleton.jsx'

// The "thinking" interstitial between the clarify loop and the plan.
// Stages echo what the real agent does: search, score, compose, time.
const STAGES = [
  'Checking restaurants near Pallavaram…',
  'Scoring candidate menus — real mains, role variety, rating…',
  'Composing a spread, not 3× one dish…',
  'Working order times backwards from when food should land…',
  'Holding the budget across every cart…',
]

export function PlanningLoader({ slots = [] }) {
  const [stage, setStage] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 520)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="planning" role="status" aria-label="Building your plan">
      <div className="planning__pulse" aria-hidden="true">
        <span>🍳</span>
      </div>
      <p className="planning__stage" key={stage}>
        {STAGES[stage]}
      </p>
      <div className="planning__skeleton" aria-hidden="true">
        {(slots.length ? slots : ['dinner']).map((s) => (
          <div key={s} className="planning__card">
            <Bone w={90} h={12} />
            <Bone w="65%" h={18} style={{ marginTop: 12 }} />
            <Bone w="90%" h={13} style={{ marginTop: 10 }} />
            <Bone w="80%" h={13} style={{ marginTop: 6 }} />
            <Bone w="40%" h={15} style={{ marginTop: 12 }} />
          </div>
        ))}
      </div>
    </div>
  )
}
