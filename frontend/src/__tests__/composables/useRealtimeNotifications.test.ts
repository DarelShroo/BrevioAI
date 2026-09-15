import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { useRealtimeNotifications } from '@/composables/useRealtimeNotifications'
import { useRealtimeStore } from '@/stores/realtime.store'
import type { SummaryJobEvent } from '@/types/events'

const toast = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
}

vi.mock('@/composables/useToast', () => ({
  useAppToast: () => toast,
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
    document_name: 'Quarterly report',
    ...overrides,
  }
}

async function mountNotifications() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'summary', component: { template: '<div />' } },
      { path: '/store', name: 'store', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  await router.isReady()
  const Comp = defineComponent({
    setup() {
      useRealtimeNotifications()
      return () => h('div')
    },
  })
  const wrapper = mount(Comp, {
    global: { plugins: [pinia, router] },
  })
  return { wrapper, router, store: useRealtimeStore() }
}

describe('useRealtimeNotifications', () => {
  it('shows a completed toast tagged with the job id', async () => {
    toast.success.mockClear()
    const { wrapper, store } = await mountNotifications()
    store.handleEvent(event(), 'user-1')
    await nextTick()
    expect(toast.success).toHaveBeenCalled()
    const [detail, summary, options] = toast.success.mock.calls[0]
    expect(summary).toMatch(/Summary completed/i)
    expect(detail).toContain('Quarterly report')
    expect(options.styleClass).toContain('job-id-job-1')
    wrapper.unmount()
  })

  it('shows a failed toast', async () => {
    toast.error.mockClear()
    const { wrapper, store } = await mountNotifications()
    store.handleEvent(
      event({
        type: 'summary.failed',
        status: 'FAILED',
        event_id: 'evt-2',
        error: { code: 'MAP', message: 'fail' },
      }),
      'user-1',
    )
    await nextTick()
    expect(toast.error).toHaveBeenCalled()
    const [detail, summary] = toast.error.mock.calls[0]
    expect(summary).toMatch(/Error generating/i)
    expect(detail).toContain('Quarterly report')
    wrapper.unmount()
  })
})
