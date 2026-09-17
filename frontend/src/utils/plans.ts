/** Format byte limits from the plan catalog for display. */
export function formatByteSize(bytes: number, locale = 'en'): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let value = bytes / 1024
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  const rounded = value >= 10 || Number.isInteger(value) ? Math.round(value) : Number(value.toFixed(1))
  return new Intl.NumberFormat(locale).format(rounded) + ' ' + units[unit]
}

export function formatPlanNumber(value: number, locale = 'en'): string {
  if (!Number.isFinite(value)) return '—'
  return new Intl.NumberFormat(locale).format(value)
}

export function formatPeriodDate(iso: string | null | undefined, locale = 'en'): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(date)
}
