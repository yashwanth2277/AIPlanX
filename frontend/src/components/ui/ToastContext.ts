import { createContext } from 'react'

export type ToastTone = 'info' | 'success' | 'error'

export type ToastInput = {
  title: string
  message?: string
  tone?: ToastTone
}

export const ToastContext = createContext<(toast: ToastInput) => void>(() => {})
