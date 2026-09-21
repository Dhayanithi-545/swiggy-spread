import { Copy, BadgePercent } from 'lucide-react'
import { Badge } from '../common/Primitives.jsx'
import { inr } from '../../utils/format.js'
import { useToast } from '../../context/ToastContext.jsx'

// A coupon. Read-only by design: the backend lists coupons after a cart
// fill but leaves applying them to the human in the Swiggy app.
export function OfferCard({ offer }) {
  const toast = useToast()

  return (
    <article className="ocard">
      <div className="ocard__stripe" aria-hidden="true">
        <BadgePercent size={20} />
      </div>
      <div className="ocard__body">
        <div className="ocard__toprow">
          <h3 className="ocard__title">{offer.title}</h3>
          {offer.codOnly && <Badge tone="amber">COD only</Badge>}
        </div>
        <p className="t-sub">{offer.description}</p>
        <p className="t-caption" style={{ marginTop: 6 }}>
          Min order {inr(offer.minOrder)} · expires in {offer.expiresIn}
        </p>
        <div className="ocard__coderow">
          <span className="ocard__code">{offer.code}</span>
          <button
            type="button"
            className="ocard__copy"
            onClick={() => {
              navigator.clipboard?.writeText(offer.code).catch(() => {})
              toast(`${offer.code} copied — apply it in the Swiggy app`, { type: 'info' })
            }}
          >
            <Copy size={13} aria-hidden="true" />
            Copy
          </button>
        </div>
      </div>
    </article>
  )
}
