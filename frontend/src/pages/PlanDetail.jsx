import { Link, useNavigate, useParams } from 'react-router-dom'
import { ChevronRight, ShoppingBag } from 'lucide-react'
import { PlanView } from '../components/plan/PlanView.jsx'
import { Badge } from '../components/common/Primitives.jsx'
import { EmptyState } from '../components/common/States.jsx'
import { useCart } from '../context/CartContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { seedPlans, planStatusMeta } from '../data/plans.js'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

export default function PlanDetail() {
  useDocumentTitle('Plan details')
  const { id } = useParams()
  const navigate = useNavigate()
  const { savedPlans, fillFromPlan } = useCart()
  const toast = useToast()

  const plan = savedPlans.find((p) => p.id === id) || seedPlans.find((p) => p.id === id)

  if (!plan) {
    return (
      <div className="page container">
        <EmptyState
          emoji="🗓️"
          title="That plan isn't here"
          message="It may have been cleared from this browser. Your other plans are safe."
          action="Back to my plans"
          actionTo="/plans"
        />
      </div>
    )
  }

  const status = planStatusMeta[plan.status] || planStatusMeta.draft

  return (
    <div className="page container">
      <nav className="detailpage__crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={13} aria-hidden="true" />
        <Link to="/plans">My plans</Link>
        <ChevronRight size={13} aria-hidden="true" />
        <span aria-current="page">{plan.createdAt}</span>
      </nav>

      <header className="plandetail__head">
        <div>
          <p className="t-caption">{plan.createdAt}</p>
          <h1 className="t-h2" style={{ marginTop: 4 }}>“{plan.request}”</h1>
        </div>
        <Badge tone={status.tone}>{status.label}</Badge>
      </header>

      <PlanView
        plan={plan}
        onApprove={() => {
          fillFromPlan(plan)
          toast('Carts filled from this plan. Ordering stays yours.', { type: 'safety', duration: 4000 })
          navigate('/carts')
        }}
        onDiscard={() => navigate('/plans')}
      />

      <div style={{ maxWidth: 680, margin: '20px auto 0' }}>
        <Link to="/carts" className="section-header__link">
          <ShoppingBag size={15} aria-hidden="true" /> See my carts
        </Link>
      </div>
    </div>
  )
}
