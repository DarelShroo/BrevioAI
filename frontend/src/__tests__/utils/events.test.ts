import { describe, expect, it } from 'vitest'
import { jobEventToastClass, jobIdFromToastClass } from '@/utils/events'

describe('toast job id helpers', () => {
  it('round-trips a job id through the toast class', () => {
    const styleClass = jobEventToastClass('entry-1')
    expect(styleClass).toContain('job-event-toast')
    expect(jobIdFromToastClass(styleClass)).toBe('entry-1')
  })

  it('returns null when the class has no job id', () => {
    expect(jobIdFromToastClass('p-toast-message')).toBeNull()
  })
})
