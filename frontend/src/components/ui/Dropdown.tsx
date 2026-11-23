import { useEffect, useId, useRef, type ReactNode } from 'react'

type DropdownProps = {
  open: boolean
  onClose: () => void
  trigger: ReactNode
  children: ReactNode
  label: string
}

export function Dropdown({ open, onClose, trigger, children, label }: DropdownProps) {
  const ref = useRef<HTMLDivElement>(null)
  const menuId = useId()

  useEffect(() => {
    if (!open) return
    const onPointer = (event: MouseEvent) => {
      if (!ref.current?.contains(event.target as Node)) onClose()
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])

  return (
    <div className="ax-menu-anchor" ref={ref}>
      <div aria-expanded={open} aria-controls={menuId} aria-haspopup="menu">
        {trigger}
      </div>
      {open && (
        <div className="ax-menu" id={menuId} role="menu" aria-label={label}>
          {children}
        </div>
      )}
    </div>
  )
}
