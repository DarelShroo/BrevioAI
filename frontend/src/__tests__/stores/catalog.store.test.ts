import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCatalogStore } from '@/stores/catalog.store'

vi.mock('@/services/brevio.service', () => ({
  fetchLanguages: vi.fn(async () => ['ENGLISH', 'AFRIKAANS', 'SPANISH', 'ZULU']),
  fetchModels: vi.fn(async () => ({
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
  })),
  fetchCategoryStyles: vi.fn(async () => ({
    education: [{ style: 'guide', source_types: ['text'] }],
  })),
  fetchOutputFormats: vi.fn(async () => ['markdown', 'html']),
  fetchSummaryLevels: vi.fn(async () => ['concise', 'detailed']),
  fetchTranscriptionProviders: vi.fn(async () => ({
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
      {
        id: 'openai',
        implemented: true,
        user_access: true,
        requires_api_key: true,
        access: 'pay_per_use',
        display_name: 'openai',
      },
    ],
    selectable: ['local_whisper', 'openai'],
    default: 'local_whisper',
    default_model: 'local_whisper',
    models: [
      {
        id: 'local_whisper',
        provider: 'local_whisper',
        status: 'stable',
        recommended: true,
        parameters: ['language'],
        display_name: 'local_whisper',
        requires_api_key: false,
        user_access: true,
      },
      {
        id: 'gpt-transcribe',
        provider: 'openai',
        vendor_model_id: 'gpt-transcribe',
        status: 'stable',
        recommended: true,
        parameters: ['prompt', 'keywords', 'languages'],
        display_name: 'gpt-transcribe',
        requires_api_key: true,
        user_access: true,
      },
    ],
  })),
}))

describe('catalog store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads catalogs once and keeps only backend prompt languages', async () => {
    const store = useCatalogStore()
    await store.loadAll()
    expect(store.languages).toEqual(['ENGLISH', 'SPANISH'])
    expect(store.stylesFor('education')).toEqual(['guide'])
    expect(store.models).toEqual(['qwen3:8b', 'gpt-4o-mini'])
    expect(store.preferredModelId()).toBe('qwen3:8b')
    expect(store.localModels.map((item) => item.id)).toEqual(['qwen3:8b'])
    expect(store.paidProviders.map((item) => item.id)).toEqual(['openai'])
    expect(store.selectableTranscriptionProviders.map((item) => item.id)).toEqual([
      'local_whisper',
      'openai',
    ])
    expect(store.defaultTranscriptionProvider).toBe('local_whisper')
    expect(store.selectableTranscriptionModels.map((item) => item.id)).toEqual([
      'local_whisper',
      'gpt-transcribe',
    ])
    expect(store.loaded).toBe(true)
  })

  it('keeps only selectable transcription providers', async () => {
    const { fetchTranscriptionProviders } = await import('@/services/brevio.service')
    vi.mocked(fetchTranscriptionProviders).mockResolvedValueOnce({
      environment: 'production',
      providers: [
        {
          id: 'local_whisper',
          implemented: true,
          user_access: false,
          requires_api_key: false,
          access: 'local',
          display_name: 'local_whisper',
        },
        {
          id: 'openai',
          implemented: true,
          user_access: true,
          requires_api_key: true,
          access: 'pay_per_use',
          display_name: 'openai',
        },
      ],
      selectable: ['openai'],
      default: 'openai',
    })
    const store = useCatalogStore()
    await store.loadAll(true)
    expect(store.selectableTranscriptionProviders.map((item) => item.id)).toEqual(['openai'])
  })
})
