import { Sparkles } from 'lucide-react'
import { Button } from '../components/common/Button.jsx'
import { PlanCard } from '../components/cards/PlanCard.jsx'
import { useCart } from '../context/CartContext.jsx'
import { seedPlans } from '../data/plans.js'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

export default function Plans() {
  useDocumentTitle('My plans')
  const { savedPlans } = useCart()

  // Session-made plans first, then the seeded history.
  const all = [...savedPlans, ...seedPlans.filter((s) => !savedPlans.some((p) => p.id === s.id))]

  return (
    <div className="page container listpage">
      <header className="listpage__head cartspage__head">
        <div>
          <h1 className="t-h1">My plans</h1>
          <p className="t-sub">Every evening Spread has planned for you — drafts included.</p>
        </div>
        <Button to="/plan" icon={Sparkles} size="sm">New plan</Button>
      </header>

      <div className="planspage__grid">
        {all.map((plan) => (
          <PlanCard key={plan.id} plan={plan} />
        ))}
      </div>
    </div>
  )
}
