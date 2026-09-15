import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SummaryDocumentReader from '@/components/markdown/SummaryDocumentReader.vue'

vi.mock('@/services/brevio.service', () => ({
  fetchSummaryMarkdown: vi.fn(async () => '# Ready\n'),
}))

import * as brevioService from '@/services/brevio.service'

describe('SummaryDocumentReader', () => {
  beforeEach(() => {
    vi.mocked(brevioService.fetchSummaryMarkdown).mockClear()
  })

  it('shows processing placeholder and does not fetch while in progress', async () => {
    const wrapper = mount(SummaryDocumentReader, {
      props: {
        folderEntryId: 'entry-1',
        resultIndex: 0,
        status: 'PROCESSING',
        phase: 'QUEUED',
      },
      global: {
        stubs: {
          MarkdownViewer: true,
        },
      },
    })
    await flushPromises()

    expect(wrapper.get('[data-testid="summary-processing"]').text()).toMatch(/not ready|aún no/i)
    expect(wrapper.get('[data-testid="summary-processing"]').text()).toContain('QUEUED')
    expect(brevioService.fetchSummaryMarkdown).not.toHaveBeenCalled()
    expect(wrapper.findComponent({ name: 'MarkdownViewer' }).exists()).toBe(false)
  })

  it('fetches markdown only when completed', async () => {
    const wrapper = mount(SummaryDocumentReader, {
      props: {
        folderEntryId: 'entry-1',
        resultIndex: 0,
        status: 'COMPLETED',
      },
      global: {
        stubs: {
          MarkdownViewer: {
            name: 'MarkdownViewer',
            props: ['source', 'loading', 'error'],
            template: '<div data-testid="md">{{ source }}</div>',
          },
        },
      },
    })
    await flushPromises()

    expect(brevioService.fetchSummaryMarkdown).toHaveBeenCalledWith('entry-1', 0)
    expect(wrapper.get('[data-testid="md"]').text()).toContain('# Ready')
  })

  it('shows failed placeholder without fetching', async () => {
    const wrapper = mount(SummaryDocumentReader, {
      props: {
        folderEntryId: 'entry-1',
        status: 'FAILED',
      },
      global: {
        stubs: { MarkdownViewer: true },
      },
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="summary-failed"]').exists()).toBe(true)
    expect(brevioService.fetchSummaryMarkdown).not.toHaveBeenCalled()
  })
})
