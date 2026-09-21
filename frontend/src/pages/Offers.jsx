import { Info } from 'lucide-react'
import { OfferCard } from '../components/cards/OfferCard.jsx'
import { foodCoupons } from '../data/offers.js'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

export default function Offers() {
  useDocumentTitle('Offers')

  return (
    <div className="page container listpage">
      <header className="listpage__head">
        <h1 className="t-h1">Offers & coupons</h1>
        <p className="t-sub">
          Spread lists coupons after filling a cart — applying one is deliberately
          left to you, in the app, at checkout.
        </p>
      </header>

      <div className="offerspage__note" role="note">
        <Info size={16} aria-hidden="true" />
        <p>
          Two honest quirks from the real Swiggy servers: agents only see
          <strong> COD-compatible</strong> food coupons, and Instamart exposes
          <strong> no coupon tools at all</strong> — whatever the docs say, the
          server wins. Check the app for Instamart offers.
        </p>
      </div>

      <div className="offerspage__grid">
        {foodCoupons.map((offer) => (
          <OfferCard key={offer.id} offer={offer} />
        ))}
      </div>
    </div>
  )
}
