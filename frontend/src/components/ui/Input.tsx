import { useId, type InputHTMLAttributes, type TextareaHTMLAttributes } from 'react'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string
  hint?: string
}

export function Input({ label, hint, id, ...props }: InputProps) {
  const generated = useId()
  const fieldId = id ?? generated
  return (
    <label className="ax-field" htmlFor={fieldId}>
      {label && <span>{label}</span>}
      <input id={fieldId} className="ax-control" {...props} />
      {hint && <small className="ax-hint">{hint}</small>}
    </label>
  )
}

type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string
  hint?: string
}

export function TextArea({ label, hint, id, ...props }: TextAreaProps) {
  const generated = useId()
  const fieldId = id ?? generated
  return (
    <label className="ax-field" htmlFor={fieldId}>
      {label && <span>{label}</span>}
      <textarea id={fieldId} className="ax-textarea" {...props} />
      {hint && <small className="ax-hint">{hint}</small>}
    </label>
  )
}
