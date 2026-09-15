import { describe, expect, it, vi } from 'vitest'
import * as brevioService from '@/services/brevio.service'
import { http, withApiKey } from '@/services/http'

vi.mock('@/services/http', () => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
  },
  withApiKey: vi.fn((config = {}) => ({
    ...config,
    headers: { ...(config.headers || {}), 'X-API-KEY': 'local_api_key_123' },
  })),
}))

describe('brevio.service', () => {
  it('parses model catalog grouped by local vs pay-per-use', async () => {
    vi.mocked(http.get).mockResolvedValueOnce({
      data: {
        status: 'success',
        data: {
          models: ['qwen3:8b', 'gpt-4o-mini'],
          catalog: [
            {
              id: 'qwen3:8b',
              provider: 'ollama',
              access: 'local',
              requires_api_key: false,
              display_name: 'qwen3:8b',
            },
            {
              id: 'gpt-4o-mini',
              provider: 'openai',
              access: 'pay_per_use',
              requires_api_key: true,
              display_name: 'gpt-4o-mini',
            },
          ],
          providers: [
            { id: 'ollama', access: 'local', requires_api_key: false },
            { id: 'openai', access: 'pay_per_use', requires_api_key: true },
          ],
        },
      },
    } as any)
    await expect(brevioService.fetchModels()).resolves.toMatchObject({
      models: ['qwen3:8b', 'gpt-4o-mini'],
      catalog: [
        expect.objectContaining({ id: 'qwen3:8b', access: 'local', requires_api_key: false }),
        expect.objectContaining({ id: 'gpt-4o-mini', access: 'pay_per_use', requires_api_key: true }),
      ],
    })
  })

  it('parses languages catalog', async () => {
    vi.mocked(http.get).mockResolvedValueOnce({
      data: { status: 'success', data: { languages: ['ENGLISH'] } },
    } as any)
    await expect(brevioService.fetchLanguages()).resolves.toEqual(['ENGLISH'])
    expect(withApiKey).toHaveBeenCalled()
  })

  it('normalizes output formats payload shapes', async () => {
    vi.mocked(http.get).mockResolvedValueOnce({
      data: { status: 'success', data: { output_format_types: ['markdown', 'html'] } },
    } as any)
    await expect(brevioService.fetchOutputFormats()).resolves.toEqual(['markdown', 'html'])

    vi.mocked(http.get).mockResolvedValueOnce({
      data: { status: 'success', data: [{ value: 'markdown' }, 'html'] },
    } as any)
    await expect(brevioService.fetchOutputFormats()).resolves.toEqual(['markdown', 'html'])
  })

  it('parses summary levels object or array', async () => {
    vi.mocked(http.get).mockResolvedValueOnce({
      data: { status: 'success', data: { summary_levels: ['concise', 'detailed'] } },
    } as any)
    await expect(brevioService.fetchSummaryLevels()).resolves.toEqual(['concise', 'detailed'])

    vi.mocked(http.get).mockResolvedValueOnce({
      data: { status: 'success', data: ['concise'] },
    } as any)
    await expect(brevioService.fetchSummaryLevels()).resolves.toEqual(['concise'])
  })

  it('parses transcription providers catalog', async () => {
    vi.mocked(http.get).mockResolvedValueOnce({
      data: {
        status: 'success',
        data: {
          environment: 'development',
          providers: [
            {
              id: 'local_whisper',
              implemented: true,
              user_access: true,
              requires_api_key: false,
              access: 'local',
              display_name: 'local_whisper',
            },
          ],
          selectable: ['local_whisper'],
          default: 'local_whisper',
        },
      },
    } as any)
    await expect(brevioService.fetchTranscriptionProviders()).resolves.toMatchObject({
      environment: 'development',
      selectable: ['local_whisper'],
    })
  })

  it('submits media with transcription provider and never stores keys', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: { status: 'success', task_id: 'task-media', folder_entry_id: 'entry-media' },
    } as any)
    const file = new File(['audio'], 'talk.mp4', { type: 'video/mp4' })
    await brevioService.submitMedia(
      [file],
      {
        language: 'SPANISH',
        model: 'gpt-4o-mini',
        category: 'education',
        style: 'guide',
        format: 'markdown',
        summary_level: 'concise',
        transcription_provider: 'local_whisper',
      },
    )
    const form = vi.mocked(http.post).mock.calls.at(-1)?.[1] as FormData
    expect(form.get('transcription_provider')).toBe('local_whisper')
    expect(form.get('api_key')).toBeNull()
    expect(http.post).toHaveBeenCalledWith('/brevio/summary-media', expect.any(FormData))
  })

  it('submits reasoning effort but never user sampling or output caps', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: { status: 'success', task_id: 'task-docs', folder_entry_id: 'entry-docs' },
    } as any)
    const file = new File(['pdf'], 'doc.pdf', { type: 'application/pdf' })
    await brevioService.submitDocuments(
      [file],
      {
        language: 'SPANISH',
        model: 'gpt-5.6',
        category: 'education',
        style: 'guide',
        format: 'markdown',
        summary_level: 'concise',
        reasoning_effort: 'low',
      },
    )
    const form = vi.mocked(http.post).mock.calls.at(-1)?.[1] as FormData
    expect(form.get('reasoning_effort')).toBe('low')
    expect(form.get('max_output_tokens')).toBeNull()
    expect(form.get('temperature')).toBeNull()
  })

  it('submits YouTube with top-level transcription provider', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: { status: 'success', task_id: 'task-yt', folder_entry_id: 'entry-yt' },
    } as any)
    await brevioService.submitYoutubePlaylist({
      prompt_config: {
        language: 'SPANISH',
        model: 'gpt-4o-mini',
        category: 'education',
        style: 'guide',
        format: 'markdown',
        summary_level: 'concise',
        transcription_provider: 'openai',
      },
      transcription_provider: 'openai',
      data: [{ url: 'https://www.youtube.com/watch?v=abc' }],
    })
    const body = vi.mocked(http.post).mock.calls.at(-1)?.[1] as {
      transcription_provider?: string
      prompt_config: { transcription_provider?: string }
    }
    expect(body.transcription_provider).toBe('openai')
    expect(body.prompt_config.transcription_provider).toBeUndefined()
    expect(http.post).toHaveBeenCalledWith('/brevio/summary-yt-playlist', expect.any(Object))
  })

  it('submits documents multipart and returns job ids', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: {
        status: 'success',
        data: { message: 'processing' },
        task_id: 'task-1',
        folder_entry_id: 'entry-1',
      },
    } as any)
    const file = new File(['pdf'], 'doc.pdf', { type: 'application/pdf' })
    const result = await brevioService.submitDocuments([file], {
      language: 'SPANISH',
      model: 'gpt-4o-mini',
      category: 'education',
      style: 'guide',
      format: 'markdown',
      summary_level: 'concise',
    })
    expect(result.task_id).toBe('task-1')
    expect(result.folder_entry_id).toBe('entry-1')
    const form = vi.mocked(http.post).mock.calls.at(-1)?.[1] as FormData
    expect(form.get('max_output_tokens')).toBeNull()
    expect(form.get('temperature')).toBeNull()
    expect(http.post).toHaveBeenCalledWith('/brevio/summary-documents', expect.any(FormData))
  })

  it('appends destination folder fields when provided', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: { status: 'success', task_id: 'task-2', folder_entry_id: 'entry-2' },
    } as any)
    const file = new File(['pdf'], 'using-asyncio-python-understanding-asynchronous.pdf', {
      type: 'application/pdf',
    })
    await brevioService.submitDocuments(
      [file],
      {
        language: 'SPANISH',
        model: 'gpt-4o-mini',
        category: 'education',
        style: 'guide',
        format: 'markdown',
        summary_level: 'concise',
      },
      { folder_name: 'Universidad' },
    )
    const form = vi.mocked(http.post).mock.calls.at(-1)?.[1] as FormData
    expect(form.get('folder_name')).toBe('Universidad')
    expect(form.get('library_folder_id')).toBeNull()
  })

  it('submits without a folder when destination is empty', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: { status: 'success', task_id: 'task-3', folder_entry_id: 'entry-3' },
    } as any)
    const file = new File(['pdf'], 'doc.pdf', { type: 'application/pdf' })
    await brevioService.submitDocuments(
      [file],
      {
        language: 'SPANISH',
        model: 'gpt-4o-mini',
        category: 'education',
        style: 'guide',
        format: 'markdown',
        summary_level: 'concise',
      },
      { library_folder_id: null, folder_name: null },
    )
    const form = vi.mocked(http.post).mock.calls.at(-1)?.[1] as FormData
    expect(form.get('folder_name')).toBeNull()
    expect(form.get('library_folder_id')).toBeNull()
  })

  it('appends every selected document to multipart FormData', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: { status: 'success', task_id: 'task-multi', folder_entry_id: 'entry-multi' },
    } as any)
    const files = [
      new File(['a'], 'a.pdf', { type: 'application/pdf' }),
      new File(['b'], 'b.docx', {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      }),
    ]
    await brevioService.submitDocuments(files, {
      language: 'SPANISH',
      model: 'gpt-4o-mini',
      category: 'education',
      style: 'guide',
      format: 'markdown',
      summary_level: 'concise',
    })
    const form = vi.mocked(http.post).mock.calls.at(-1)?.[1] as FormData
    expect(form.getAll('files')).toHaveLength(2)
    expect((form.getAll('files')[0] as File).name).toBe('a.pdf')
    expect((form.getAll('files')[1] as File).name).toBe('b.docx')
  })

  it('fetches summary markdown as text', async () => {
    vi.mocked(http.get).mockResolvedValueOnce({
      data: {
        text: async () => '# Hello\n\nWorld',
      },
    } as never)
    await expect(brevioService.fetchSummaryMarkdown('entry-1', 0)).resolves.toContain('# Hello')
    expect(http.get).toHaveBeenCalledWith(
      '/brevio/download/entry-1',
      expect.objectContaining({
        params: { format: 'md', result_index: 0 },
        responseType: 'blob',
      }),
    )
  })
})
