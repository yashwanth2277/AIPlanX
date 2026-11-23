export function Spinner({ label }: { label?: string }) {
  return (
    <span className="ax-spinner" role="status">
      <span className="ax-spinner-dot" aria-hidden />
      {label}
    </span>
  )
}
