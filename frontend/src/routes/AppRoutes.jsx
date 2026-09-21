import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { MainLayout } from '../layouts/MainLayout.jsx'
import { Bone } from '../components/common/Skeleton.jsx'

// Route-level code splitting — every page loads on demand.
const Home = lazy(() => import('../pages/Home.jsx'))
const PlanBuilder = lazy(() => import('../pages/PlanBuilder.jsx'))
const Restaurants = lazy(() => import('../pages/Restaurants.jsx'))
const RestaurantDetail = lazy(() => import('../pages/RestaurantDetail.jsx'))
const Instamart = lazy(() => import('../pages/Instamart.jsx'))
const SearchPage = lazy(() => import('../pages/SearchPage.jsx'))
const Carts = lazy(() => import('../pages/Carts.jsx'))
const Plans = lazy(() => import('../pages/Plans.jsx'))
const PlanDetail = lazy(() => import('../pages/PlanDetail.jsx'))
const Offers = lazy(() => import('../pages/Offers.jsx'))
const Profile = lazy(() => import('../pages/Profile.jsx'))
const NotFound = lazy(() => import('../pages/NotFound.jsx'))

function PageFallback() {
  return (
    <div className="container" style={{ paddingTop: 40 }} role="status" aria-label="Loading page">
      <Bone w={220} h={28} />
      <Bone w={340} h={15} style={{ marginTop: 14 }} />
      <Bone h={220} r={16} style={{ marginTop: 28 }} />
    </div>
  )
}

export function AppRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/plan" element={<PlanBuilder />} />
          <Route path="/restaurants" element={<Restaurants />} />
          <Route path="/restaurants/:id" element={<RestaurantDetail />} />
          <Route path="/instamart" element={<Instamart />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/carts" element={<Carts />} />
          <Route path="/plans" element={<Plans />} />
          <Route path="/plans/:id" element={<PlanDetail />} />
          <Route path="/offers" element={<Offers />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
