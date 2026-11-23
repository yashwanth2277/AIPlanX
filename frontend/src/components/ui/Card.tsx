import type { HTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

export function Card({
  className,
  hover = false,
  padded = true,
  ...props
}: HTMLAttributes<HTMLDivElement> & { hover?: boolean; padded?: boolean }) {
  return (
    <div
      className={cn('ax-card', padded && 'ax-card-pad', hover && 'ax-card-hover', className)}
      {...props}
    />
  )
}
