import { ref } from 'vue'
import { parseApiError } from '@/utils/errors'

export function useAsyncState<T>() {
  const data = ref<T | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(false)

  async function run(task: () => Promise<T>): Promise<T | null> {
    loading.value = true
    error.value = null
    try {
      const result = await task()
      data.value = result as T
      return result
    } catch (err) {
      error.value = parseApiError(err)
      return null
    } finally {
      loading.value = false
    }
  }

  function reset() {
    data.value = null
    error.value = null
    loading.value = false
  }

  return { data, error, loading, run, reset }
}
