import { useContext } from 'react'
import { ToastContext } from './ToastContext'

export type { ToastInput } from './ToastContext'

export function useToast() {
  return useContext(ToastContext)
}
