import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Sparkles, ArrowRight, ShieldAlert } from 'lucide-react'
import { ClarifyChat } from '../components/plan/ClarifyChat.jsx'
import { PlanningLoader } from '../components/plan/PlanningLoader.jsx'
import { PlanView } from '../components/plan/PlanView.jsx'
import { Button } from '../components/common/Button.jsx'
import { buildPlan } from '../utils/planner.js'
import { useCart } from '../context/CartContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

const EXAMPLES = [
  '6 friends Saturday 8pm, budget 3000, 2 are veg',
  'order dinner for 4 tonight',
  'snacks and dessert for the match, we are 8, no spice',
]

// The product's main flow: request -> clarify -> plan -> fill carts.
// Phases: ask (no query yet) | clarify | planning | plan | blocked
export default function PlanBuilder() {
  useDocumentTitle('Plan an evening')
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const { fillFromPlan, savePlan } = useCart()
  const toast = useToast()

  const query = params.get('q') || ''
  const [phase, setPhase] = useState(query ? 'clarify' : 'ask')
  const [plan, setPlan] = useState(null)
  const [planningSlots, setPlanningSlots] = useState([])
  const [blockedReason, setBlockedReason] = useState('')
  const [draft, setDraft] = useState('')

  // A new ?q= (from the hero or a restart) resets the flow.
  useEffect(() => {
    setPhase(query ? 'clarify' : 'ask')
    setPlan(null)
    setBlockedReason('')
  }, [query])

  const startPlanning = (req) => {
    setPlanningSlots(req.slots)
    setPhase('planning')
    setTimeout(() => {
      const built = buildPlan(req)
      setPlan(built)
      savePlan(built)
      setPhase('plan')
    }, 2400)
  }

  const approve = () => {
    fillFromPlan(plan)
    toast('Carts filled. Nothing was ordered — that part is yours.', { type: 'safety', duration: 4200 })
    navigate('/carts')
  }

  return (
    <div className="page container planpage">
      <header className="planpage__head">
        <h1 className="t-h1">
          <Sparkles size={22} aria-hidden="true" className="planpage__spark" />
          Plan an evening
        </h1>
        <p className="t-sub">
          Say it like you'd say it to a friend. Spread asks only what changes the
          outcome, then shows the whole plan before touching a cart.
        </p>
      </header>

      {phase === 'ask' && (
        <div className="planpage__ask anim-fade-up">
          <form
            className="planpage__form"
            onSubmit={(e) => {
              e.preventDefault()
              if (draft.trim()) setParams({ q: draft.trim() })
            }}
          >
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="6 friends coming Saturday 8pm, budget 3000, 2 are vegetarian…"
              aria-label="Describe your gathering"
              autoFocus
            />
            <button type="submit" className="planpage__go" disabled={!draft.trim()} aria-label="Start planning">
              <ArrowRight size={18} aria-hidden="true" />
            </button>
          </form>
          <p className="t-label" style={{ margin: '22px 0 10px' }}>Or start from one of these</p>
          <div className="planpage__examples">
            {EXAMPLES.map((ex) => (
              <button key={ex} type="button" className="planpage__example" onClick={() => setParams({ q: ex })}>
                “{ex}”
              </button>
            ))}
          </div>
        </div>
      )}

      {phase === 'clarify' && (
        <ClarifyChat
          key={query}
          initialText={query}
          onComplete={startPlanning}
          onBlocked={(reason) => {
            setBlockedReason(reason)
            setPhase('blocked')
          }}
        />
      )}

      {phase === 'planning' && <PlanningLoader slots={planningSlots} />}

      {phase === 'plan' && plan && (
        <PlanView
          plan={plan}
          onApprove={approve}
          onDiscard={() => {
            setParams({})
            setDraft('')
          }}
        />
      )}

      {phase === 'blocked' && (
        <div className="planpage__blocked anim-fade-up" role="alert">
          <ShieldAlert size={28} aria-hidden="true" />
          <h2 className="t-h3">The guardrail stopped this one</h2>
          <p className="t-sub">{blockedReason}</p>
          <Button variant="secondary" onClick={() => setParams({})} style={{ marginTop: 18 }}>
            Try a different request
          </Button>
        </div>
      )}
    </div>
  )
}
