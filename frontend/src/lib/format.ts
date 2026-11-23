export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

export function timestamp(value: string | null | undefined): number {
  if (!value) return 0
  const parsed = new Date(value).getTime()
  return Number.isNaN(parsed) ? 0 : parsed
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return 'Unknown date'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

export function formatWhen(value: string | null | undefined): string {
  if (!value) return 'Unknown time'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

export function slugSessionName(value: string): string {
  const slug = value.replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^[-_]+|[-_]+$/g, '').slice(0, 40)
  return slug || 'session'
}

export function isValidSessionName(value: string): boolean {
  return /^[A-Za-z0-9_-]{1,64}$/.test(value)
}
