import { describe, expect, it } from 'vitest'
import { formatByteSize, formatPeriodDate, formatPlanNumber } from '@/utils/plans'

describe('plans utils', () => {
  it('formats byte sizes from catalog limits', () => {
    expect(formatByteSize(10485760, 'en')).toBe('10 MB')
    expect(formatByteSize(52428800, 'en')).toBe('50 MB')
  })

  it('formats plan numbers and period dates', () => {
    expect(formatPlanNumber(2000, 'en')).toBe('2,000')
    expect(formatPeriodDate('2026-09-01T00:00:00+00:00', 'en')).toMatch(/2026/)
  })
})
