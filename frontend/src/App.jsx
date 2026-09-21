import { BrowserRouter } from 'react-router-dom'
import { AppRoutes } from './routes/AppRoutes.jsx'
import { ToastProvider } from './context/ToastContext.jsx'
import { CartProvider } from './context/CartContext.jsx'
import { FavoritesProvider } from './context/FavoritesContext.jsx'
import { ErrorBoundary } from './components/common/States.jsx'

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ToastProvider>
          <CartProvider>
            <FavoritesProvider>
              <AppRoutes />
            </FavoritesProvider>
          </CartProvider>
        </ToastProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
