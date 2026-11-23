import type { ReactNode } from 'react'
import { Inbox, type LucideIcon } from 'lucide-react'

export function EmptyState({
  icon: Icon = Inbox,
  title,
  message,
  action,
}: {
  icon?: LucideIcon
  title: string
  message: string
  action?: ReactNode
}) {
  return (
    <div className="ax-empty">
      <Icon aria-hidden size={22} />
      <h2>{title}</h2>
      <p>{message}</p>
      {action}
    </div>
  )
}
