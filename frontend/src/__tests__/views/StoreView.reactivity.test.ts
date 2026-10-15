import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import StoreView from '@/views/StoreView.vue'
import { useRealtimeStore } from '@/stores/realtime.store'
import * as userService from '@/services/user.service'
import * as libraryStore from '@/stores/library.store'
import { nextTick } from 'vue'

vi.mock('@/services/user.service')
vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ query: {} })),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}))
vi.mock('@/composables/useToast', () => ({
  useAppToast: vi.fn(() => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  })),
}))
vi.mock('@/stores/library.store', () => ({
  useLibraryStore: vi.fn(() => ({
    load: vi.fn().mockResolvedValue(undefined),
    folders: [],
    unfiledCount: 0
  }))
}))

describe('StoreView Progress Reactivity', () => {
  const mockEntry = {
    id: 'entry-1',
    user_id: 'user-1',
    name: 'Test Summary',
    results: [
      {
        id: 'doc-1',
        name: 'test.pdf',
        status: 'PROCESSING',
        phase: 'MAP_RUNNING',
        progress: 10,
        weight: 1
      }
    ],
    status: 'PROCESSING',
    progress: 10,
    stage: 'MAP_RUNNING'
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(userService.listEntries).mockResolvedValue([mockEntry])
    vi.mocked(userService.listFolders).mockResolvedValue({ folders: [], unfiled_count: 1 })
    vi.mocked(userService.pollEntries).mockResolvedValue([mockEntry])
  })

  it('updates progress bar automatically when SSE events are received', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    
    const realtime = useRealtimeStore()

    const wrapper = mount(StoreView, {
      global: {
        plugins: [pinia],
        stubs: {
          RouterLink: true,
          FolderOpen: true,
          Inbox: true,
          Filter: true,
          StoreMetrics: true,
          StoreFolderBar: true,
          StoreToolbar: true,
          Button: true,
          StateBlock: {
            template: '<div class="state-block"><slot></slot><slot name="empty"></slot></div>',
          },
          DataTable: {
            template: '<div><slot></slot></div>'
          },
          Dialog: true,
          Drawer: {
            template: '<div class="drawer-stub"><slot></slot></div>'
          },
          Column: true,
          ProgressBar: {
            template: '<div class="progress-bar-stub" :data-progress="progress" :data-stage="stage">{{ progress }}%</div>',
            props: ['progress', 'stage', 'status']
          },
          StatusBadge: true
        }
      }
    })

    // Wait for initial load
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 0)) // Flush promises

    // Open detail
    ;(wrapper.vm as any).openDetail(mockEntry)
    await nextTick()

    // Assert initial state in detail view
    const progressBar = wrapper.find('.progress-bar-stub')
    expect(progressBar.exists()).toBe(true)
    expect(progressBar.attributes('data-progress')).toBe('10')
    expect(progressBar.attributes('data-stage')).toBe('MAP_RUNNING')

    // Simulate backend SSE event progressing to 50%
    realtime.handleEvent({
      type: 'summary.progress',
      job_id: 'entry-1',
      document_id: 'doc-1',
      status: 'PROCESSING',
      progress: 50,
      stage: 'REDUCE_RUNNING',
      global_progress: 50,
      timestamp: new Date().toISOString(),
      event_id: 'event-1'
    }, 'user-1')
    
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 0))

    // Assert UI reacted without reload
    const updatedProgressBar = wrapper.find('.progress-bar-stub')
    expect(updatedProgressBar.attributes('data-progress')).toBe('50')
    expect(updatedProgressBar.attributes('data-stage')).toBe('REDUCE_RUNNING')

    // Simulate completion
    realtime.handleEvent({
      type: 'summary.progress',
      job_id: 'entry-1',
      document_id: 'doc-1',
      status: 'COMPLETED',
      progress: 100,
      stage: 'COMPLETED',
      global_progress: 100,
      timestamp: new Date().toISOString(),
      event_id: 'event-2'
    }, 'user-1')

    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 0))

    // Assert completion updates
    const finalProgressBar = wrapper.find('.progress-bar-stub')
    const finalStatusBadge = wrapper.find('status-badge-stub')
    expect(finalProgressBar.exists() || finalStatusBadge.exists()).toBe(true)
    expect(realtime.entry('entry-1')?.results?.[0]?.status).toBe('COMPLETED')
    expect(realtime.entry('entry-1')?.results?.[0]?.phase).toBe('COMPLETED')
  })
})
