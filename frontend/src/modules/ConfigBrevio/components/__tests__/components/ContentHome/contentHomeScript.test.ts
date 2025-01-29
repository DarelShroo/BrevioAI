import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ContentHome from '../../../ContentHome/ContentHome.vue'

describe('ContentHome.ts', () => {
  let pinia: any
  let wrapper: any

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    wrapper = mount(ContentHome, {
      global: {
        plugins: [pinia],
      },
      template: '<div />',
    })
  })

  it('should initialize with default reactive states', () => {
    const { loading, isUserSearched, error, result_content } = wrapper.vm
    expect(loading).toBe(false)
    expect(isUserSearched).toBe(false)
    expect(error).toBe(false)
    expect(result_content).toBe('')
  })

  it('should update `loading` state when handleLoadingUpdate is called', () => {
    wrapper.vm.handleLoadingUpdate(true)
    expect(wrapper.vm.loading).toBe(true)

    wrapper.vm.handleLoadingUpdate(false)
    expect(wrapper.vm.loading).toBe(false)
  })

  it('should update `isUserSearched` state when handleisUserSearchedUpdate is called', () => {
    wrapper.vm.handleisUserSearchedUpdate(true)
    expect(wrapper.vm.isUserSearched).toBe(true)

    wrapper.vm.handleisUserSearchedUpdate(false)
    expect(wrapper.vm.isUserSearched).toBe(false)
  })

  it('should update `error` state when handleisErrorUpdate is called', () => {
    wrapper.vm.handleisErrorUpdate(true)
    expect(wrapper.vm.error).toBe(true)

    wrapper.vm.handleisErrorUpdate(false)
    expect(wrapper.vm.error).toBe(false)
  })

  it('should update `result_content` correctly when handlResultContentUpdate is called with a matching string', () => {
    const testString = 'Transcription(summary=Test Summary, message=Some message)'
    wrapper.vm.handlResultContentUpdate(testString)
    expect(wrapper.vm.result_content).toBe('Test Summary')
  })

  it('should handle empty or invalid strings in `handlResultContentUpdate` gracefully', () => {
    const invalidInputs = ['', 'invalid string', 'summary=, message']
    invalidInputs.forEach((input) => {
      wrapper.vm.handlResultContentUpdate(input)
      expect(wrapper.vm.result_content).toBe('')
    })
  })

  it('should reset all states to default values', () => {
    wrapper.vm.handleLoadingUpdate(true)
    wrapper.vm.handleisUserSearchedUpdate(true)
    wrapper.vm.handleisErrorUpdate(true)
    wrapper.vm.handlResultContentUpdate('Transcription(summary=Reset Test, message=Message)')

    wrapper.vm.handleLoadingUpdate(false)
    wrapper.vm.handleisUserSearchedUpdate(false)
    wrapper.vm.handleisErrorUpdate(false)
    wrapper.vm.handlResultContentUpdate('')

    expect(wrapper.vm.loading).toBe(false)
    expect(wrapper.vm.isUserSearched).toBe(false)
    expect(wrapper.vm.error).toBe(false)
    expect(wrapper.vm.result_content).toBe('')
  })

  it('should handle undefined input in handlResultContentUpdate', () => {
    wrapper.vm.handlResultContentUpdate(undefined)
    expect(wrapper.vm.result_content).toBe('')
  })

  it('should handle null input in handlResultContentUpdate', () => {
    wrapper.vm.handlResultContentUpdate(null)
    expect(wrapper.vm.result_content).toBe('')
  })

  it('should ignore extra whitespace in handlResultContentUpdate input', () => {
    const testString = '  Transcription(summary=  Test Summary   , message=Message)  '
    wrapper.vm.handlResultContentUpdate(testString)
    expect(wrapper.vm.result_content).toBe('Test Summary')
  })

  it('should handle unexpected string formats in handlResultContentUpdate gracefully', () => {
    const testString = 'Transcription(summary, message=Test Message)'
    wrapper.vm.handlResultContentUpdate(testString)
    expect(wrapper.vm.result_content).toBe('')
  })

  it('', () => {
    const hasImage = wrapper.vm.backgroundImage
    expect(hasImage).toBeTruthy()
  })
})
