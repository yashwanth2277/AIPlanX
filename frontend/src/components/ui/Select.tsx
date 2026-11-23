import { useId, type SelectHTMLAttributes } from 'react'

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string
  hint?: string
}

export function Select({ label, hint, id, children, ...props }: SelectProps) {
  const generated = useId()
  const fieldId = id ?? generated
  return (
    <label className="ax-field" htmlFor={fieldId}>
      {label && <span>{label}</span>}
      <select id={fieldId} className="ax-control" {...props}>
        {children}
      </select>
      {hint && <small className="ax-hint">{hint}</small>}
    </label>
  )
}
