import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { useJobPolling } from '@/composables/useJobPolling'
import * as userService from '@/services/user.service'

vi.mock('@/services/user.service', () => ({
  pollEntries: vi.fn(),
}))

describe('useJobPolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.mocked(userService.pollEntries).mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function mountPolling(options?: { intervalMs?: number; maxAttempts?: number }) {
    let api: ReturnType<typeof useJobPolling> | null = null
    const Comp = defineComponent({
      setup() {
        api = useJobPolling(options)
        return () => h('div')
      },
    })
    const wrapper = mount(Comp)
    return { wrapper, get api() { return api! } }
  }

  it('polls until terminal COMPLETED', async () => {
    vi.mocked(userService.pollEntries)
      .mockResolvedValueOnce([
        {
          id: 'entry-1',
          user_id: 'u1',
          name: 'Job',
          results: [{ status: 'PROCESSING' }],
        },
      ])
      .mockResolvedValueOnce([
        {
          id: 'entry-1',
          user_id: 'u1',
          name: 'Job',
          results: [{ status: 'COMPLETED', download_location: 'data/x' }],
        },
      ])

    const { api, wrapper } = mountPolling({ intervalMs: 100, maxAttempts: 5 })
    const startPromise = api.start(['entry-1'])
    await flushPromises()
    expect(api.entries.value[0]?.results?.[0]?.status).toBe('PROCESSING')
    expect(api.done.value).toBe(false)

    await vi.advanceTimersByTimeAsync(100)
    await flushPromises()
    await startPromise

    expect(api.done.value).toBe(true)
    expect(api.entries.value[0]?.results?.[0]?.status).toBe('COMPLETED')
    wrapper.unmount()
  })

  it('records timeout when max attempts exceeded', async () => {
    vi.mocked(userService.pollEntries).mockResolvedValue([
      {
        id: 'entry-1',
        user_id: 'u1',
        name: 'Job',
        results: [{ status: 'PROCESSING' }],
      },
    ])

    const { api, wrapper } = mountPolling({ intervalMs: 50, maxAttempts: 2 })
    const startPromise = api.start(['entry-1'])
    await flushPromises()
    await vi.advanceTimersByTimeAsync(50)
    await flushPromises()
    await startPromise

    expect(api.done.value).toBe(false)
    expect(api.error.value).toMatch(/timed out/i)
    wrapper.unmount()
  })

  it('captures poll errors', async () => {
    vi.mocked(userService.pollEntries).mockRejectedValueOnce(new Error('poll failed'))
    const { api, wrapper } = mountPolling({ intervalMs: 50, maxAttempts: 1 })
    await api.start(['entry-1'])
    await nextTick()
    expect(api.error.value).toContain('poll failed')
    wrapper.unmount()
  })
})
