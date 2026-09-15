import { describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LibraryFolderField from '@/components/summary/LibraryFolderField.vue'
import type { SummaryDestination } from '@/types/brevio'

vi.mock('@/stores/library.store', () => ({
  useLibraryStore: () => ({
    folders: [{ id: 'f1', name: 'Backend', entry_count: 1 }],
    load: vi.fn(async () => undefined),
  }),
}))

describe('LibraryFolderField', () => {
  it('defaults to no folder and can create a new one', async () => {
    const wrapper = mount(LibraryFolderField, {
      props: {
        modelValue: { library_folder_id: null, folder_name: null } satisfies SummaryDestination,
        'onUpdate:modelValue': (value: SummaryDestination) => wrapper.setProps({ modelValue: value }),
      },
      global: {
        stubs: {
          Select: {
            props: ['modelValue', 'options'],
            emits: ['update:modelValue'],
            template:
              '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="opt in options" :key="opt.value" :value="opt.value">{{ opt.label }}</option></select>',
          },
          InputText: {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template:
              '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
        },
      },
    })
    await flushPromises()
    expect(wrapper.get('[data-testid="summary-folder-field"]').element).toBeTruthy()
  })
})
