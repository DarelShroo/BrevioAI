import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as userService from '@/services/user.service'
import {
  connectSummaryEvents,
  disconnectSummaryEvents,
} from '@/services/sse.client'
import { useAuthStore } from '@/stores/auth.store'
import type { SummaryJobEvent } from '@/types/events'
import type { FolderEntry } from '@/types/user'
import { entryId } from '@/utils/entries'

const LAST_EVENT_KEY = 'brevio:sse:last-event-id'

type SummaryEventListener = (event: SummaryJobEvent) => void

function lastEventStorageKey(userId: string) {
  return `${LAST_EVENT_KEY}:${userId}`
}

export const useRealtimeStore = defineStore('realtime', () => {
  const connected = ref(false)
  const connecting = ref(false)
  const entriesById = ref<Record<string, FolderEntry>>({})
  const seenEventIds = new Set<string>()
  const listeners = new Set<SummaryEventListener>()
  let connectionUserId: string | null = null

  const trackedJobs = computed(() => Object.values(entriesById.value))

  function entry(jobId: string | null | undefined): FolderEntry | null {
    if (!jobId) return null
    return entriesById.value[jobId] ?? null
  }

  function upsertEntry(item: FolderEntry) {
    const id = entryId(item)
    if (!id) return
    entriesById.value = { ...entriesById.value, [id]: item }
  }

  function subscribe(listener: SummaryEventListener) {
    listeners.add(listener)
    return () => {
      listeners.delete(listener)
    }
  }

  function rememberEventId(userId: string, eventId: string) {
    if (!eventId || typeof sessionStorage === 'undefined') return
    sessionStorage.setItem(lastEventStorageKey(userId), eventId)
  }

  function storedEventId(userId: string): string | null {
    if (typeof sessionStorage === 'undefined') return null
    return sessionStorage.getItem(lastEventStorageKey(userId))
  }

  async function refreshJob(jobId: string) {
    if (!jobId) return null
    try {
      const entries = await userService.pollEntries([jobId])
      const item = entries[0]
      if (item) upsertEntry(item)
      return item ?? null
    } catch {
      return entry(jobId)
    }
  }

  async function trackJob(jobId: string) {
    return refreshJob(jobId)
  }

  function handleEvent(event: SummaryJobEvent, userId: string) {
    const eventId = event.event_id || `${event.job_id}:${event.document_id}:${event.status}`
    if (seenEventIds.has(eventId)) return
    seenEventIds.add(eventId)
    if (seenEventIds.size > 500) {
      const first = seenEventIds.values().next().value
      if (first) seenEventIds.delete(first)
    }
    rememberEventId(userId, event.event_id)
    void refreshJob(event.job_id)
    listeners.forEach((listener) => listener(event))
  }

  function connect() {
    const auth = useAuthStore()
    if (!auth.isAuthenticated || !auth.userId) return
    if (connectionUserId === auth.userId && (connected.value || connecting.value)) return
    disconnect()
    connecting.value = true
    connectionUserId = auth.userId
    const userId = auth.userId
    connectSummaryEvents({
      lastEventId: storedEventId(userId),
      onOpen: () => {
        connected.value = true
        connecting.value = false
      },
      onEvent: (event) => handleEvent(event, userId),
      onError: () => {
        connected.value = false
        connecting.value = false
      },
      onAuthError: () => {
        connected.value = false
        connecting.value = false
        connectionUserId = null
        void auth.logout()
      },
    })
  }

  function disconnect() {
    disconnectSummaryEvents()
    connected.value = false
    connecting.value = false
    connectionUserId = null
  }

  function reset() {
    disconnect()
    entriesById.value = {}
    seenEventIds.clear()
  }

  return {
    connected,
    connecting,
    entriesById,
    trackedJobs,
    entry,
    upsertEntry,
    subscribe,
    refreshJob,
    trackJob,
    handleEvent,
    connect,
    disconnect,
    reset,
  }
})
