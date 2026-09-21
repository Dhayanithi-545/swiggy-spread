import { EmptyState } from '../components/common/States.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

export default function NotFound() {
  useDocumentTitle('Page not found')
  return (
    <div className="page container" style={{ display: 'grid', placeItems: 'center' }}>
      <div>
        <p className="notfound__code" aria-hidden="true">404</p>
        <EmptyState
          emoji="🍽️"
          title="This table doesn't exist"
          message="The page you're looking for was never on the menu. Head home and plan something instead."
          action="Back to home"
          actionTo="/"
        />
      </div>
    </div>
  )
}
