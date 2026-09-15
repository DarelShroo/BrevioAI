import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import StoreFolderBar from '@/components/store/StoreFolderBar.vue'

describe('StoreFolderBar', () => {
  it('emits create, select, rename and delete', async () => {
    const wrapper = mount(StoreFolderBar, {
      props: {
        folders: [{ id: 'f1', name: 'Backend', entry_count: 2 }],
        unfiledCount: 3,
        currentScope: 'f1',
      },
    })

    await wrapper.get('[data-testid="store-create-folder"]').trigger('click')
    expect(wrapper.emitted('create')).toBeTruthy()

    await wrapper.get('[data-testid="store-scope-unfiled"]').trigger('click')
    expect(wrapper.emitted('select')?.[0]).toEqual(['unfiled'])

    await wrapper.get('[data-testid="store-rename-folder"]').trigger('click')
    expect(wrapper.emitted('rename')?.[0]?.[0]).toMatchObject({ id: 'f1' })

    await wrapper.get('[data-testid="store-delete-folder"]').trigger('click')
    expect(wrapper.emitted('remove')?.[0]?.[0]).toMatchObject({ name: 'Backend' })
  })

  it('shows empty unfiled count', () => {
    const wrapper = mount(StoreFolderBar, {
      props: {
        folders: [],
        unfiledCount: 0,
        currentScope: 'all',
      },
    })
    expect(wrapper.text()).toContain('Unfiled')
    expect(wrapper.find('[data-testid="store-rename-folder"]').exists()).toBe(false)
  })
})
