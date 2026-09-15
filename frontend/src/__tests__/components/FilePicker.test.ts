import { describe, expect, it } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import FilePicker from '@/components/summary/FilePicker.vue'

function makeFile(name: string, type = 'application/pdf') {
  return new File(['content'], name, { type })
}

const stubs = {
  FileUpload: {
    name: 'FileUpload',
    template: '<button type="button" data-testid="stub-upload" />',
  },
  Button: {
    props: ['label'],
    emits: ['click'],
    template: '<button type="button" @click="$emit(\'click\')">{{ label }}</button>',
  },
  Message: { template: '<div><slot /></div>' },
}

describe('FilePicker', () => {
  it('accumulates multiple valid files and can remove one', async () => {
    const wrapper = mount(FilePicker, {
      props: {
        files: [],
        accept: '.pdf',
        hint: 'Pick PDFs',
        validator: (file: File) => file.name.endsWith('.pdf'),
        invalidMessage: 'Only PDF',
        'onUpdate:files': (value: File[]) => wrapper.setProps({ files: value }),
      },
      global: { stubs },
    })

    await wrapper.findComponent({ name: 'FileUpload' }).vm.$emit('select', {
      files: [makeFile('a.pdf'), makeFile('b.pdf')],
    })
    await flushPromises()

    expect(wrapper.props('files')).toHaveLength(2)
    expect(wrapper.get('[data-testid="file-picker-count"]').text()).toMatch(/2/)
    expect(wrapper.get('[data-testid="file-picker-list"]').text()).toContain('a.pdf')
    expect(wrapper.get('[data-testid="file-picker-list"]').text()).toContain('b.pdf')

    await wrapper.findAll('[data-testid="file-picker-remove"]')[0].trigger('click')
    await flushPromises()
    expect(wrapper.props('files')).toHaveLength(1)
    expect(wrapper.props('files')?.[0]?.name).toBe('b.pdf')
  })

  it('rejects invalid extensions without mutating selection', async () => {
    const wrapper = mount(FilePicker, {
      props: {
        files: [],
        accept: '.pdf',
        hint: 'Pick PDFs',
        validator: (file: File) => file.name.endsWith('.pdf'),
        invalidMessage: 'Only PDF',
        'onUpdate:files': (value: File[]) => wrapper.setProps({ files: value }),
      },
      global: { stubs },
    })

    await wrapper.findComponent({ name: 'FileUpload' }).vm.$emit('select', {
      files: [makeFile('notes.txt', 'text/plain')],
    })
    await flushPromises()

    expect(wrapper.props('files')).toHaveLength(0)
    expect(wrapper.get('[data-testid="file-picker-error"]').text()).toContain('Only PDF')
  })

  it('replaces selection when multiple is disabled', async () => {
    const wrapper = mount(FilePicker, {
      props: {
        files: [makeFile('old.pdf')],
        multiple: false,
        accept: '.pdf',
        hint: 'Pick one',
        validator: () => true,
        invalidMessage: 'bad',
        'onUpdate:files': (value: File[]) => wrapper.setProps({ files: value }),
      },
      global: { stubs },
    })

    await wrapper.findComponent({ name: 'FileUpload' }).vm.$emit('select', {
      files: [makeFile('new.pdf'), makeFile('extra.pdf')],
    })
    await flushPromises()

    expect(wrapper.props('files')).toHaveLength(1)
    expect(wrapper.props('files')?.[0]?.name).toBe('new.pdf')
  })
})
