import { cn } from '../../lib/cn'
import { toneForStatus } from './badgeTone'

export function StatusBadge({ label, title }: { label: string; title?: string }) {
  return (
    <span className={cn('ax-badge', `ax-badge-${toneForStatus(label)}`)} title={title}>
      <i />
      {label}
    </span>
  )
}
