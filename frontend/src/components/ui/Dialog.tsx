import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { IconButton } from './IconButton'

type DialogProps = {
  open: boolean
  title: string
  description?: string
  onClose: () => void
  children: ReactNode
  wide?: boolean
  closeDisabled?: boolean
}

export function Dialog({ open, title, description, onClose, children, wide = false, closeDisabled = false }: DialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null
    dialogRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !closeDisabled) onClose()
    }
    document.addEventListener('keydown', onKey)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = previousOverflow
      previouslyFocused?.focus()
    }
  }, [open, closeDisabled, onClose])

  if (!open) return null

  return createPortal(
    <div
      className="ax-dialog-root"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !closeDisabled) onClose()
      }}
    >
      <div
        ref={dialogRef}
        className={wide ? 'ax-dialog ax-dialog-wide' : 'ax-dialog'}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        tabIndex={-1}
      >
        <div className="ax-dialog-head">
          <div>
            <h2 id="dialog-title">{title}</h2>
            {description && <p className="ax-lead">{description}</p>}
          </div>
          <IconButton aria-label="Close dialog" onClick={onClose} disabled={closeDisabled}>
            <X size={18} />
          </IconButton>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  )
}
