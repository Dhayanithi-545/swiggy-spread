import { Hero } from '../components/sections/Hero.jsx'
import { HowItWorks } from '../components/sections/HowItWorks.jsx'
import { SectionHeader } from '../components/common/Primitives.jsx'
import { CategoryCard } from '../components/cards/CategoryCard.jsx'
import { RestaurantCard } from '../components/cards/RestaurantCard.jsx'
import { ProductCard } from '../components/cards/ProductCard.jsx'
import { GridSkeleton, RestaurantCardSkeleton } from '../components/common/Skeleton.jsx'
import { categories } from '../data/categories.js'
import { restaurants } from '../data/restaurants.js'
import { products } from '../data/instamart.js'
import { useFakeLoading } from '../hooks/useFakeLoading.js'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

export default function Home() {
  useDocumentTitle('One sentence, the whole evening sorted')
  const loading = useFakeLoading(700)

  const topRestaurants = [...restaurants].sort((a, b) => b.rating - a.rating).slice(0, 8)
  const quickPicks = products.filter((p) => p.slot === 'snacks').slice(0, 6)

  return (
    <div className="page" style={{ paddingBottom: 0 }}>
      <Hero />

      <section className="home-section container" aria-labelledby="cat-title">
        <SectionHeader title="What's on your mind?" to="/search" linkLabel="Search everything" />
        <div className="hscroll" id="cat-title">
          {categories.map((c) => (
            <CategoryCard key={c.id} category={c} />
          ))}
        </div>
      </section>

      <section className="home-section container" aria-labelledby="top-title">
        <SectionHeader
          title="Top restaurants near you"
          subtitle="Pallavaram, Chennai — the planner scores these the same way you'd browse them"
          to="/restaurants"
        />
        {loading ? (
          <GridSkeleton count={4} className="rgrid" Card={RestaurantCardSkeleton} />
        ) : (
          <div className="rgrid">
            {topRestaurants.slice(0, 4).map((r) => (
              <RestaurantCard key={r.id} restaurant={r} />
            ))}
          </div>
        )}
      </section>

      <section className="home-section container" aria-labelledby="im-title">
        <SectionHeader
          title="Party snacks in 15 minutes"
          subtitle="Instamart handles snacks and dessert — the fast half of every plan"
          to="/instamart"
        />
        <div className="hscroll">
          {quickPicks.map((p) => (
            <div key={p.id} style={{ width: 172 }}>
              <ProductCard product={p} />
            </div>
          ))}
        </div>
      </section>

      <HowItWorks />

      <section className="home-section container" aria-labelledby="more-title">
        <SectionHeader title="More places worth a spread" to="/restaurants" />
        {loading ? (
          <GridSkeleton count={4} className="rgrid" Card={RestaurantCardSkeleton} />
        ) : (
          <div className="rgrid">
            {topRestaurants.slice(4, 8).map((r) => (
              <RestaurantCard key={r.id} restaurant={r} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
