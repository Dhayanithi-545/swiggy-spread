import { Outlet } from 'react-router-dom'
import { Header } from '../components/navigation/Header.jsx'
import { BottomNav } from '../components/navigation/BottomNav.jsx'
import { Footer } from '../components/navigation/Footer.jsx'
import { ScrollToTop } from '../components/common/ScrollToTop.jsx'

export function MainLayout() {
  return (
    <>
      <ScrollToTop />
      <a href="#main" className="skip-link">Skip to content</a>
      <Header />
      <main id="main">
        <Outlet />
      </main>
      <Footer />
      <BottomNav />
    </>
  )
}
