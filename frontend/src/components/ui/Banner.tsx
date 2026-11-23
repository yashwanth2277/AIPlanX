import type { ReactNode } from 'react'
import { Button } from './Button'

export function Banner({ children, onDismiss }: { children: ReactNode; onDismiss?: () => void }) {
  return (
    <div className="ax-banner" role="alert">
      <div style={{ flex: 1 }}>{children}</div>
      {onDismiss && <Button variant="ghost" size="sm" onClick={onDismiss}>Dismiss</Button>}
    </div>
  )
}
