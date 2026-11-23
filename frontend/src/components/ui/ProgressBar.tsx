export function ProgressBar({ value, label = 'Completion' }: { value: number; label?: string }) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div className="ax-progress">
      <div className="ax-progress-label">
        <span>{label}</span>
        <span>{Math.round(clamped)}%</span>
      </div>
      <div className="ax-progress-track" role="progressbar" aria-valuenow={Math.round(clamped)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
        <span style={{ width: `${clamped}%` }} />
      </div>
    </div>
  )
}

export function ProgressRing({ value, label }: { value: number; label: string }) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div className="ax-ring" style={{ ['--value' as string]: `${clamped}%` }} role="img" aria-label={`${label} ${Math.round(clamped)} percent`}>
      <span>{Math.round(clamped)}%</span>
    </div>
  )
}
