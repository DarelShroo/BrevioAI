import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import StoreEntryCard from '@/components/store/StoreEntryCard.vue'
import type { FolderEntry } from '@/types/user'

describe('StoreEntryCard download visibility', () => {
  const base: FolderEntry = {
    id: 'abcdef123456',
    user_id: 'u1',
    name: 'Mi carpeta',
    results: [
      { name: 'a.pdf', status: 'COMPLETED' },
      { name: 'b.pdf', status: 'COMPLETED' },
    ],
  }

  it('hides download when no completed results are ready', () => {
    const wrapper = mount(StoreEntryCard, {
      props: {
        entry: base,
        canDownload: false,
      },
      global: {
        stubs: {
          StatusBadge: true,
        },
      },
    })
    expect(wrapper.find('[data-testid="store-download-btn"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Mi carpeta')
    expect(wrapper.text()).not.toContain('a.pdf')
  })

  it('shows download for multi-result entries so the picker can open', async () => {
    const wrapper = mount(StoreEntryCard, {
      props: {
        entry: base,
        canDownload: true,
      },
      global: {
        stubs: {
          StatusBadge: true,
        },
      },
    })
    expect(wrapper.find('[data-testid="store-download-btn"]').exists()).toBe(true)
    await wrapper.get('[data-testid="store-download-btn"]').trigger('click')
    expect(wrapper.emitted('download')).toHaveLength(1)
  })
})
