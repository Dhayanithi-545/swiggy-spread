import { Component } from 'react'
import { RotateCcw } from 'lucide-react'
import { Button } from './Button.jsx'

// Empty and error states — designed, not apologetic afterthoughts.

export function EmptyState({ emoji = '🍽️', title, message, action, actionTo, onAction }) {
  return (
    <div className="state-block anim-fade-up" role="status">
      <div className="state-block__emoji" aria-hidden="true">
        {emoji}
      </div>
      <h3 className="t-h3">{title}</h3>
      {message && <p className="t-sub state-block__msg">{message}</p>}
      {action && (
        <div style={{ marginTop: 20 }}>
          <Button to={actionTo} onClick={onAction} size="md">
            {action}
          </Button>
        </div>
      )}
    </div>
  )
}

export function ErrorState({ title = 'Something went wrong', message = 'Please try again in a moment.', onRetry }) {
  return (
    <div className="state-block" role="alert">
      <div className="state-block__emoji" aria-hidden="true">
        🍳
      </div>
      <h3 className="t-h3">{title}</h3>
      <p className="t-sub state-block__msg">{message}</p>
      {onRetry && (
        <div style={{ marginTop: 20 }}>
          <Button variant="secondary" icon={RotateCcw} onClick={onRetry}>
            Try again
          </Button>
        </div>
      )}
    </div>
  )
}

export class ErrorBoundary extends Component {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error) {
    console.error('Spread UI error:', error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container" style={{ paddingTop: 80 }}>
          <ErrorState
            title="This screen burnt the toast"
            message="An unexpected error broke this page. Reloading usually fixes it."
            onRetry={() => window.location.reload()}
          />
        </div>
      )
    }
    return this.props.children
  }
}
