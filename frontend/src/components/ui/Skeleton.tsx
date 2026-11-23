import { cn } from '../../lib/cn'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('ax-skeleton', className)} aria-hidden />
}

export function CardSkeletonGrid() {
  return (
    <div className="ax-card-grid" aria-hidden>
      {Array.from({ length: 6 }, (_, index) => (
        <Skeleton key={index} className="h-44" />
      ))}
    </div>
  )
}

export function PageSkeleton() {
  return (
    <div className="ax-stack" aria-busy="true" aria-live="polite">
      <span className="ax-spinner"><span className="ax-spinner-dot" /> Loading</span>
      <Skeleton className="h-28" />
      <div className="ax-metrics">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
    </div>
  )
}
