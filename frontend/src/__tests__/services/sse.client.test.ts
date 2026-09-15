import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  decodeSummaryEvent,
  parseSseBlock,
  parseSseBuffer,
  SseClient,
  connectSummaryEvents,
  disconnectSummaryEvents,
  resetSseClientForTests,
} from '@/services/sse.client'
import type { SummaryJobEvent } from '@/types/events'

function summaryEvent(overrides: Partial<SummaryJobEvent> = {}): SummaryJobEvent {
  return {
    type: 'summary.completed',
    event_id: '1',
    job_id: 'job-1',
    document_id: 'doc-1',
    status: 'COMPLETED',
    timestamp: '2026-09-14T12:00:00Z',
    document_name: 'Doc.pdf',
    ...overrides,
  }
}

function streamFrom(chunks: string[]) {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
}

describe('sse parser', () => {
  it('parses id, event and json data', () => {
    const parsed = parseSseBlock(
      [
        'id: 9-0',
        'event: summary.completed',
        `data: ${JSON.stringify(summaryEvent({ event_id: '' }))}`,
      ].join('\n'),
    )
    expect(parsed?.id).toBe('9-0')
    expect(parsed?.event).toBe('summary.completed')
    const decoded = decodeSummaryEvent(parsed!)
    expect(decoded?.job_id).toBe('job-1')
    expect(decoded?.event_id).toBe('9-0')
  })

  it('ignores comments and incomplete buffers', () => {
    const { events, rest } = parseSseBuffer(': keepalive\n\nid: 1\nevent: summary.failed\ndata: {')
    expect(events).toHaveLength(0)
    expect(rest).toContain('data: {')
  })
})

describe('SseClient', () => {
  afterEach(() => {
    resetSseClientForTests()
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('connects with credentials and emits events', async () => {
    const onEvent = vi.fn()
    const frame = [
      'id: 1',
      'event: summary.completed',
      `data: ${JSON.stringify(summaryEvent())}`,
      '',
      '',
    ].join('\n')
    const fetchMock = vi.fn(async () => {
      return {
        ok: true,
        status: 200,
        body: streamFrom([frame]),
      }
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new SseClient({
      onEvent,
      reconnect: false,
    })
    client.connect()
    await vi.waitFor(() => expect(onEvent).toHaveBeenCalledTimes(1))
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const firstCall = fetchMock.mock.calls.at(0) as unknown as [string, RequestInit]
    expect(firstCall[1].credentials).toBe('include')
    expect((firstCall[1].headers as Record<string, string>).Authorization).toBeUndefined()
    expect(onEvent.mock.calls[0][0].type).toBe('summary.completed')
    client.disconnect()
  })

  it('prevents duplicate connections', async () => {
    const fetchMock = vi.fn(
      () =>
        new Promise(() => {
          /* hang */
        }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const client = new SseClient({
      onEvent: vi.fn(),
      reconnect: false,
    })
    client.connect()
    client.connect()
    await Promise.resolve()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    client.disconnect()
  })

  it('reconnects after a dropped connection', async () => {
    vi.useFakeTimers()
    const onEvent = vi.fn()
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: streamFrom([
          `id: 2\nevent: summary.failed\ndata: ${JSON.stringify(
            summaryEvent({ type: 'summary.failed', status: 'FAILED', event_id: '2' }),
          )}\n\n`,
        ]),
      })
    vi.stubGlobal('fetch', fetchMock)
    const client = new SseClient({ onEvent })
    client.connect()
    await Promise.resolve()
    await vi.advanceTimersByTimeAsync(600)
    await vi.waitFor(() => expect(onEvent).toHaveBeenCalled())
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    client.disconnect()
  })

  it('stops on 401 and does not reconnect', async () => {
    const onAuthError = vi.fn()
    const fetchMock = vi.fn(async () => ({ ok: false, status: 401, body: null }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new SseClient({
      onEvent: vi.fn(),
      onAuthError,
    })
    client.connect()
    await vi.waitFor(() => expect(onAuthError).toHaveBeenCalled())
    expect(client.active).toBe(false)
  })

  it('module singleton avoids duplicate clients', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise(() => {
            /* hang */
          }),
      ),
    )
    const first = connectSummaryEvents({ onEvent: vi.fn() })
    const second = connectSummaryEvents({ onEvent: vi.fn() })
    expect(first).toBe(second)
    disconnectSummaryEvents()
  })
})
