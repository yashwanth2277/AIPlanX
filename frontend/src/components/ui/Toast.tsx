import { useCallback, useState, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { IconButton } from './IconButton'
import { ToastContext, type ToastInput } from './ToastContext'

type ToastRecord = ToastInput & { id: number; tone: NonNullable<ToastInput['tone']> }

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const push = useCallback((toast: ToastInput) => {
    const id = Date.now() + Math.floor(Math.random() * 1000)
    const record: ToastRecord = { ...toast, id, tone: toast.tone ?? 'info' }
    setToasts((current) => [...current, record])
    window.setTimeout(() => dismiss(id), 4600)
  }, [dismiss])

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="ax-toast-wrap" aria-live="polite">
        {toasts.map((toast) => (
          <div className={`ax-toast ax-toast-${toast.tone}`} key={toast.id} role={toast.tone === 'error' ? 'alert' : 'status'}>
            <div>
              <strong>{toast.title}</strong>
              {toast.message && <p>{toast.message}</p>}
            </div>
            <IconButton aria-label="Dismiss notification" onClick={() => dismiss(toast.id)}>
              <X size={16} />
            </IconButton>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
