import { onUnmounted, ref } from 'vue'
import * as userService from '@/services/user.service'
import type { FolderEntry } from '@/types/user'
import { entryId, entryStatus, isTerminalStatus } from '@/utils/entries'
import { parseApiError } from '@/utils/errors'

export interface UseJobPollingOptions {
  intervalMs?: number
  maxAttempts?: number
}

export function useJobPolling(options: UseJobPollingOptions = {}) {
  const intervalMs = options.intervalMs ?? 2500
  const maxAttempts = options.maxAttempts ?? 120

  const entries = ref<FolderEntry[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const done = ref(false)

  let timer: ReturnType<typeof setTimeout> | null = null
  let attempts = 0
  let stopped = false

  function clearTimer() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  function stop() {
    stopped = true
    clearTimer()
  }

  async function pollOnce(entryIds: string[]) {
    loading.value = true
    error.value = null
    try {
      entries.value = await userService.pollEntries(entryIds)
      const allTerminal = entries.value.every((entry) =>
        isTerminalStatus(entryStatus(entry)),
      )
      done.value = allTerminal && entries.value.length > 0
      return entries.value
    } catch (err) {
      error.value = parseApiError(err)
      return entries.value
    } finally {
      loading.value = false
    }
  }

  async function start(entryIds: string[]) {
    stop()
    stopped = false
    attempts = 0
    done.value = false
    entries.value = []

    const tick = async () => {
      if (stopped) return
      attempts += 1
      await pollOnce(entryIds)
      if (done.value || attempts >= maxAttempts || stopped) {
        if (attempts >= maxAttempts && !done.value) {
          error.value = error.value || 'Polling timed out.'
        }
        return
      }
      timer = setTimeout(tick, intervalMs)
    }

    await tick()
  }

  onUnmounted(stop)

  return {
    entries,
    loading,
    error,
    done,
    start,
    stop,
    pollOnce,
    entryId,
  }
}
