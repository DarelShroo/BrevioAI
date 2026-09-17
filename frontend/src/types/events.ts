import type { JobStatus } from '@/types/user'

export type SummaryEventType = 'summary.completed' | 'summary.failed' | 'summary.progress'

export interface SummaryEventError {
  code: string
  message: string
}

export interface SummaryJobEvent {
  type: SummaryEventType
  event_id: string
  job_id: string
  document_id: string
  status: JobStatus | string
  timestamp: string
  document_name?: string
  error?: SummaryEventError | null
  progress?: number
  stage?: string
  global_progress?: number
}

export function isSummaryJobEvent(value: unknown): value is SummaryJobEvent {
  if (!value || typeof value !== 'object') return false
  const event = value as Record<string, unknown>
  return (
    (event.type === 'summary.completed' || event.type === 'summary.failed' || event.type === 'summary.progress') &&
    typeof event.job_id === 'string' &&
    typeof event.document_id === 'string'
  )
}
