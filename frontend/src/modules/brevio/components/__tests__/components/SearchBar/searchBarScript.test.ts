import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { api } from '@/utils/api'
import SearchBar from '../../../SearchBar/SearchBar.vue'

vi.mock('@/utils/api', () => ({
  api: vi.fn(() => ({
    post: vi.fn(),
  })),
}))

vi.mock('@/ConfigBrevioRequest/composables/useStoreNotification', () => ({
  useStoreNotification: vi.fn(() => ({
    configNotification: vi.fn(),
  })),
}))

vi.mock('@/ConfigBrevioRequest/composables/useStoreDeviceType', () => ({
  useStoreDeviceType: vi.fn(() => ({
    placement: { value: 'top-right' },
  })),
}))

describe('SearchBar.ts', () => {
  let wrapper: any

  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)

    wrapper = mount(SearchBar, {
      props: {
        loading: false,
        isUserSearched: false,
        error: false,
        result_content: '',
      },
    })

    vi.clearAllMocks()
  })

  it('should initialize with default props', () => {
    expect(wrapper.props().loading).toBe(false)
    expect(wrapper.props().isUserSearched).toBe(false)
    expect(wrapper.props().error).toBe(false)
    expect(wrapper.props().result_content).toBe('')
  })

  it('should emit updates for loading, isUserSearched, and result_content on successful search', async () => {
    const mockApiResponse = {
      summary_result: ['Test Summary'],
    }
    const mockPost = vi.fn().mockResolvedValue(mockApiResponse)
    ;(api as any).mockImplementation(() => ({ post: mockPost }))

    wrapper.vm.searchValue = 'http://example.com'
    await wrapper.vm.onSearch()

    expect(mockPost).toHaveBeenCalledWith('http://localhost:8000/brevio', {
      url: 'http://example.com',
      language: 'es',
    })
    expect(wrapper.emitted()).toHaveProperty('update:loading')
    expect(wrapper.emitted('update:loading')[0]).toEqual([true])
    expect(wrapper.emitted('update:isUserSearched')[0]).toEqual([true])
    expect(wrapper.emitted('update:result_content')[0]).toEqual(['Test Summary'])
    expect(wrapper.emitted('update:loading')[1]).toEqual([false])
  })



  it('should handle API failure and trigger error notification', async () => {
    const mockPost = vi.fn().mockRejectedValue(new Error('API failure'))
    ;(api as any).mockImplementation(() => ({ post: mockPost }))

    wrapper.vm.searchValue = 'http://example.com'
    await wrapper.vm.onSearch()

    expect(mockPost).toHaveBeenCalledWith('http://localhost:8000/brevio', {
      url: 'http://example.com',
      language: 'es',
    })

    expect(wrapper.emitted()).toHaveProperty('update:error')

  })

  it('should not call API if searchValue is empty', async () => {
    const mockPost = vi.fn()
    ;(api as any).mockImplementation(() => ({ post: mockPost }))

    wrapper.vm.searchValue = ''
    await wrapper.vm.onSearch()

    expect(mockPost).not.toHaveBeenCalled()
    expect(wrapper.emitted('update:loading')[0]).toEqual([false])
  })
})
