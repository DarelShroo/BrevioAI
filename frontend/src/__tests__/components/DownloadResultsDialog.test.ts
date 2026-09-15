import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DownloadResultsDialog from '@/components/store/DownloadResultsDialog.vue'
import type { FolderEntry } from '@/types/user'

const multiEntry: FolderEntry = {
  id: 'e1',
  user_id: 'u1',
  name: 'Batch',
  results: [
    { name: 'alpha.pdf', status: 'COMPLETED', index: 0 },
    { name: 'beta.pdf', status: 'COMPLETED', index: 1 },
    { name: 'gamma.pdf', status: 'FAILED', index: 2 },
  ],
}

describe('DownloadResultsDialog', () => {
  it('lists completed results and confirms selected indexes', async () => {
    const wrapper = mount(DownloadResultsDialog, {
      props: {
        visible: true,
        entry: multiEntry,
        preferredIndex: 1,
        initialFormat: 'md',
      },
      global: {
        stubs: {
          Dialog: {
            template: '<div><slot /></div>',
          },
          Select: true,
          Button: {
            template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
          },
          Checkbox: {
            props: ['modelValue', 'value', 'binary'],
            emits: ['update:modelValue'],
            template:
              '<input type="checkbox" :checked="isChecked" @change="onChange" />',
            computed: {
              isChecked() {
                if (this.binary) return !!this.modelValue
                return Array.isArray(this.modelValue) && this.modelValue.includes(this.value)
              },
            },
            methods: {
              onChange(event: Event) {
                const checked = (event.target as HTMLInputElement).checked
                if (this.binary) {
                  this.$emit('update:modelValue', checked)
                  return
                }
                const current = Array.isArray(this.modelValue) ? [...this.modelValue] : []
                if (checked && !current.includes(this.value)) current.push(this.value)
                if (!checked) {
                  const next = current.filter((item) => item !== this.value)
                  this.$emit('update:modelValue', next)
                  return
                }
                this.$emit('update:modelValue', current)
              },
            },
          },
        },
      },
    })

    await flushPromises()
    expect(wrapper.find('[data-testid="store-download-option-0"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="store-download-option-1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="store-download-option-2"]').exists()).toBe(false)

    await wrapper.get('[data-testid="store-download-confirm"]').trigger('click')
    expect(wrapper.emitted('confirm')?.[0]?.[0]).toEqual({ indexes: [1], format: 'md' })
  })
})
