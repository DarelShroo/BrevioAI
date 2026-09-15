import { describe, expect, it } from 'vitest'
import { useAsyncState } from '@/composables/useAsyncState'

describe('useAsyncState', () => {
  it('stores successful data', async () => {
    const state = useAsyncState<number>()
    const result = await state.run(async () => 42)
    expect(result).toBe(42)
    expect(state.data.value).toBe(42)
    expect(state.error.value).toBeNull()
  })

  it('captures errors', async () => {
    const state = useAsyncState<number>()
    await state.run(async () => {
      throw new Error('boom')
    })
    expect(state.data.value).toBeNull()
    expect(state.error.value).toBe('boom')
  })
})
