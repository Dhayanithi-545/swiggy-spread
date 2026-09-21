import { useMemo, useState } from 'react'
import { Zap } from 'lucide-react'
import { ProductCard } from '../components/cards/ProductCard.jsx'
import { GridSkeleton, ProductCardSkeleton } from '../components/common/Skeleton.jsx'
import { EmptyState } from '../components/common/States.jsx'
import { products, instamartCategories } from '../data/instamart.js'
import { useFakeLoading } from '../hooks/useFakeLoading.js'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

export default function Instamart() {
  useDocumentTitle('Instamart')
  const [cat, setCat] = useState('all')
  const loading = useFakeLoading(500, cat)

  const list = useMemo(
    () => (cat === 'all' ? products : products.filter((p) => p.category === cat)),
    [cat],
  )

  return (
    <div className="page container listpage">
      <header className="impage__banner">
        <div>
          <h1 className="t-h1">Instamart</h1>
          <p className="impage__tag">
            <Zap size={15} fill="currentColor" aria-hidden="true" />
            Groceries and party supplies in ~15 minutes — the fast half of every plan
          </p>
        </div>
        <span className="impage__emoji" aria-hidden="true">⚡🛒</span>
      </header>

      <div className="impage__cats" role="tablist" aria-label="Categories">
        <button
          type="button"
          role="tab"
          aria-selected={cat === 'all'}
          className={`impage__cat ${cat === 'all' ? 'impage__cat--active' : ''}`}
          onClick={() => setCat('all')}
        >
          <span aria-hidden="true">🛍️</span> All
        </button>
        {instamartCategories.map((c) => (
          <button
            key={c.id}
            type="button"
            role="tab"
            aria-selected={cat === c.id}
            className={`impage__cat ${cat === c.id ? 'impage__cat--active' : ''}`}
            onClick={() => setCat(c.id)}
          >
            <span aria-hidden="true">{c.emoji}</span> {c.label}
          </button>
        ))}
      </div>

      {loading ? (
        <GridSkeleton count={10} className="pgrid" Card={ProductCardSkeleton} />
      ) : list.length === 0 ? (
        <EmptyState emoji="🧺" title="Shelf's empty" message="Nothing in this aisle yet." />
      ) : (
        <div className="pgrid anim-fade-up">
          {list.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      )}
    </div>
  )
}
