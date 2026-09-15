import { getApiBaseUrl } from '@/services/http'
import { isSummaryJobEvent, type SummaryJobEvent } from '@/types/events'

export interface ParsedSseEvent {
  id?: string
  event?: string
  data?: string
}

export type SummaryEventHandler = (event: SummaryJobEvent) => void

export interface SseClientOptions {
  lastEventId?: string | null
  onEvent: SummaryEventHandler
  onOpen?: () => void
  onError?: (error: unknown) => void
  onAuthError?: () => void
  reconnect?: boolean
}

const MAX_BACKOFF_MS = 15_000
const BASE_BACKOFF_MS = 500

export function parseSseBlock(block: string): ParsedSseEvent | null {
  const parsed: ParsedSseEvent = {}
  for (const rawLine of block.split('\n')) {
    const line = rawLine.replace(/\r$/, '')
    if (!line || line.startsWith(':')) continue
    const idx = line.indexOf(':')
    const field = idx === -1 ? line : line.slice(0, idx)
    const value = idx === -1 ? '' : line.slice(idx + 1).replace(/^ /, '')
    if (field === 'id') parsed.id = value
    else if (field === 'event') parsed.event = value
    else if (field === 'data') parsed.data = parsed.data ? `${parsed.data}\n${value}` : value
  }
  if (!parsed.id && !parsed.event && !parsed.data) return null
  return parsed
}

export function parseSseBuffer(buffer: string): { events: ParsedSseEvent[]; rest: string } {
  const parts = buffer.split('\n\n')
  const rest = parts.pop() ?? ''
  const events: ParsedSseEvent[] = []
  for (const block of parts) {
    const parsed = parseSseBlock(block)
    if (parsed) events.push(parsed)
  }
  return { events, rest }
}

export function decodeSummaryEvent(parsed: ParsedSseEvent): SummaryJobEvent | null {
  if (!parsed.data) return null
  try {
    const payload = JSON.parse(parsed.data) as unknown
    if (!isSummaryJobEvent(payload)) return null
    if (parsed.id && !payload.event_id) payload.event_id = parsed.id
    return payload
  } catch {
    return null
  }
}

export class SseClient {
  private abort: AbortController | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private attempt = 0
  private closed = false
  private connecting = false
  private lastEventId: string | null
  private options: SseClientOptions

  constructor(options: SseClientOptions) {
    this.options = options
    this.lastEventId = options.lastEventId ?? null
  }

  get active(): boolean {
    return !this.closed && this.abort !== null
  }

  connect() {
    if (this.closed) return
    if (this.connecting || this.abort) return
    void this.open()
  }

  disconnect() {
    this.closed = true
    this.connecting = false
    this.clearReconnect()
    this.abort?.abort()
    this.abort = null
  }

  private clearReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private scheduleReconnect() {
    if (this.closed || this.options.reconnect === false) return
    this.clearReconnect()
    const delay = Math.min(MAX_BACKOFF_MS, BASE_BACKOFF_MS * 2 ** this.attempt)
    this.attempt += 1
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      void this.open()
    }, delay)
  }

  private async open() {
    if (this.closed || this.connecting) return
    this.connecting = true
    const abort = new AbortController()
    this.abort = abort
    try {
      const headers: Record<string, string> = {
        Accept: 'text/event-stream',
      }
      if (this.lastEventId) headers['Last-Event-ID'] = this.lastEventId
      const response = await fetch(`${getApiBaseUrl()}/events/stream`, {
        method: 'GET',
        headers,
        credentials: 'include',
        signal: abort.signal,
      })
      if (response.status === 401 || response.status === 403) {
        this.options.onAuthError?.()
        this.disconnect()
        return
      }
      if (!response.ok || !response.body) {
        throw new Error(`SSE connection failed (${response.status})`)
      }
      this.attempt = 0
      this.options.onOpen?.()
      await this.read(response.body, abort.signal)
      if (!this.closed) this.scheduleReconnect()
    } catch (error) {
      if (this.closed || abort.signal.aborted) return
      this.options.onError?.(error)
      this.scheduleReconnect()
    } finally {
      if (this.abort === abort) this.abort = null
      this.connecting = false
    }
  }

  private async read(body: ReadableStream<Uint8Array>, signal: AbortSignal) {
    const reader = body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    try {
      while (!signal.aborted) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parsed = parseSseBuffer(buffer)
        buffer = parsed.rest
        for (const item of parsed.events) {
          if (item.id) this.lastEventId = item.id
          const event = decodeSummaryEvent(item)
          if (event) this.options.onEvent(event)
        }
      }
    } finally {
      try {
        reader.releaseLock()
      } catch {
        // already released
      }
    }
  }
}

let singleton: SseClient | null = null

export function connectSummaryEvents(options: SseClientOptions): SseClient {
  if (singleton?.active) return singleton
  singleton?.disconnect()
  singleton = new SseClient(options)
  singleton.connect()
  return singleton
}

export function disconnectSummaryEvents() {
  singleton?.disconnect()
  singleton = null
}

export function resetSseClientForTests() {
  disconnectSummaryEvents()
}
