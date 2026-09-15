import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useRealtimeStore } from '@/stores/realtime.store'
import { useAuthStore } from '@/stores/auth.store'
import * as userService from '@/services/user.service'
import * as sseClient from '@/services/sse.client'
import type { SummaryJobEvent } from '@/types/events'

vi.mock('@/services/user.service', () => ({
  pollEntries: vi.fn(),
  getMe: vi.fn(),
}))

vi.mock('@/services/sse.client', () => ({
  connectSummaryEvents: vi.fn(),
  disconnectSummaryEvents: vi.fn(),
}))

function event(overrides: Partial<SummaryJobEvent> = {}): SummaryJobEvent {
  return {
    type: 'summary.completed',
    event_id: 'evt-1',
    job_id: 'job-1',
    document_id: 'doc-1',
    status: 'COMPLETED',
    timestamp: '2026-09-14T12:00:00Z',
    document_name: 'Doc.pdf',
    ...overrides,
  }
}

describe('realtime store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    sessionStorage.clear()
    vi.mocked(userService.pollEntries).mockReset()
    vi.mocked(sseClient.connectSummaryEvents).mockReset()
    vi.mocked(sseClient.disconnectSummaryEvents).mockReset()
  })

  it('connects once for the authenticated user', () => {
    const auth = useAuthStore()
    auth.authenticated = true
    auth.profile = {
      id: 'user-1',
      username: 'tester1',
      email: 't@example.com',
      user_credit: 0,
      folder_id: null,
    }
    const store = useRealtimeStore()
    store.connect()
    store.connect()
    expect(sseClient.connectSummaryEvents).toHaveBeenCalledTimes(1)
  })

  it('updates entries from the backend when an event arrives', async () => {
    vi.mocked(userService.pollEntries).mockResolvedValue([
      {
        id: 'job-1',
        user_id: 'user-1',
        name: 'Doc.pdf',
        results: [{ name: 'Doc.pdf', status: 'COMPLETED' }],
      },
    ])
    const store = useRealtimeStore()
    const received: SummaryJobEvent[] = []
    store.subscribe((item) => received.push(item))
    store.handleEvent(event(), 'user-1')
    await vi.waitFor(() => expect(store.entry('job-1')?.results[0]?.status).toBe('COMPLETED'))
    expect(received).toHaveLength(1)
    store.handleEvent(event(), 'user-1')
    expect(received).toHaveLength(1)
  })

  it('tracks a job with a single fetch', async () => {
    vi.mocked(userService.pollEntries).mockResolvedValue([
      {
        id: 'job-2',
        user_id: 'user-1',
        name: 'Media',
        results: [{ status: 'PROCESSING' }],
      },
    ])
    const store = useRealtimeStore()
    await store.trackJob('job-2')
    expect(userService.pollEntries).toHaveBeenCalledTimes(1)
    expect(store.entry('job-2')?.results[0]?.status).toBe('PROCESSING')
  })

  it('disconnects and clears job cache on reset', async () => {
    vi.mocked(userService.pollEntries).mockResolvedValue([
      { id: 'job-1', user_id: 'u', name: 'x', results: [] },
    ])
    const store = useRealtimeStore()
    await store.trackJob('job-1')
    store.reset()
    expect(sseClient.disconnectSummaryEvents).toHaveBeenCalled()
    expect(store.entry('job-1')).toBeNull()
  })
})
