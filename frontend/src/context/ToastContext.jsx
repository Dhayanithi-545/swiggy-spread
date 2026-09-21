import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { CheckCircle2, Info, AlertTriangle, ShieldCheck } from 'lucide-react'

const ToastContext = createContext(null)

const ICONS = {
  success: CheckCircle2,
  info: Info,
  warn: AlertTriangle,
  safety: ShieldCheck,
}

let nextId = 1

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timers = useRef({})

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id))
    clearTimeout(timers.current[id])
    delete timers.current[id]
  }, [])

  const toast = useCallback(
    (message, { type = 'success', duration = 2800 } = {}) => {
      const id = nextId++
      setToasts((t) => [...t.slice(-2), { id, message, type }])
      timers.current[id] = setTimeout(() => dismiss(id), duration)
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => {
          const Icon = ICONS[t.type] || Info
          return (
            <button
              key={t.id}
              className={`toast toast--${t.type}`}
              onClick={() => dismiss(t.id)}
              aria-label={`Dismiss: ${t.message}`}
            >
              <Icon size={17} aria-hidden="true" />
              <span>{t.message}</span>
            </button>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside ToastProvider')
  return ctx
}
