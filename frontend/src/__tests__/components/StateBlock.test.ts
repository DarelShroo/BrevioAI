import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import StateBlock from '@/components/common/StateBlock.vue'

describe('StateBlock', () => {
  const stubs = {
    Message: { template: '<div class="msg"><slot /></div>', props: ['severity'] },
    ProgressSpinner: { template: '<div class="spinner" />' },
    Button: {
      template: '<button @click="$emit(\'click\')"><slot />{{ label }}</button>',
      props: ['label', 'icon', 'severity'],
    },
  }

  it('shows loading state', () => {
    const wrapper = mount(StateBlock, {
      props: { loading: true },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('Loading')
  })

  it('shows error message and emits retry', async () => {
    const wrapper = mount(StateBlock, {
      props: { error: 'Boom' },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('Boom')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('retry')).toBeTruthy()
  })

  it('shows empty message and default slot otherwise', () => {
    const empty = mount(StateBlock, {
      props: { empty: true, emptyMessage: 'Nothing here' },
      global: { stubs },
    })
    expect(empty.text()).toContain('Nothing here')

    const content = mount(StateBlock, {
      props: { empty: false },
      slots: { default: '<p>Ready</p>' },
      global: { stubs },
    })
    expect(content.text()).toContain('Ready')
  })
})
