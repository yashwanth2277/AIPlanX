export type BadgeTone = 'accent' | 'success' | 'warning' | 'danger' | 'neutral'

export function toneForStatus(label: string): BadgeTone {
  const value = label.toLowerCase()
  if (/(complete|on track)/.test(value)) return 'success'
  if (/(delay|attention|block|hold)/.test(value)) return 'warning'
  if (/(progress|active|planning|plan ready)/.test(value)) return 'accent'
  if (/fail|error/.test(value)) return 'danger'
  return 'neutral'
}
