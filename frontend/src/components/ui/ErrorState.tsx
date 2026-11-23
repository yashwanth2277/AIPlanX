import { TriangleAlert } from 'lucide-react'
import { Button } from './Button'

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
}: {
  title?: string
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="ax-error" role="alert">
      <TriangleAlert aria-hidden size={20} />
      <h2>{title}</h2>
      <p>{message}</p>
      {onRetry && <Button variant="secondary" onClick={onRetry}>Try again</Button>}
    </div>
  )
}
