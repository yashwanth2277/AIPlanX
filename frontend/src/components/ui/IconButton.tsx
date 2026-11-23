import type { ButtonHTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

export function IconButton({ className, type = 'button', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type={type} className={cn('ax-icon-btn', className)} {...props} />
}
