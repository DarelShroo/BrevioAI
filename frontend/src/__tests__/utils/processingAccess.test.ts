import { describe, expect, it } from 'vitest'
import {
  canStartProcessing,
  isSummaryModelBlocked,
  isTranscriptionKeyMissing,
} from '@/utils/processingAccess'
import type { CatalogModel } from '@/utils/models'

const paid: CatalogModel = {
  id: 'gpt-4o-mini',
  provider: 'openai',
  access: 'pay_per_use',
  requires_api_key: true,
  display_name: 'gpt-4o-mini',
}

const local: CatalogModel = {
  id: 'qwen3:8b',
  provider: 'ollama',
  access: 'local',
  requires_api_key: false,
  display_name: 'qwen3:8b',
}

describe('processingAccess', () => {
  it('blocks paid summary models without a key or platform credential', () => {
    const providerWithKey = { id: 'openai', access: 'pay_per_use' as const, requires_api_key: true, has_platform_credential: true }
    const providerWithoutKey = { id: 'openai', access: 'pay_per_use' as const, requires_api_key: true, has_platform_credential: false }
    expect(isSummaryModelBlocked(paid, new Set(), providerWithoutKey)).toBe(true)
    expect(isSummaryModelBlocked(paid, new Set(['openai']), providerWithoutKey)).toBe(false)
    expect(isSummaryModelBlocked(paid, new Set(), providerWithKey)).toBe(false)
    expect(isSummaryModelBlocked(local, new Set(), undefined)).toBe(false)
  })

  it('requires an OpenAI key only for paid transcription providers', () => {
    expect(isTranscriptionKeyMissing({ id: 'openai', requires_api_key: true }, new Set())).toBe(true)
    expect(
      isTranscriptionKeyMissing({ id: 'openai', requires_api_key: true }, new Set(['openai'])),
    ).toBe(false)
    expect(
      isTranscriptionKeyMissing({ id: 'local_whisper', requires_api_key: false }, new Set()),
    ).toBe(false)
  })

  it('blocks media submit when transcription key is missing', () => {
    expect(
      canStartProcessing({
        summaryBlocked: false,
        transcriptionBlocked: true,
        needsTranscription: true,
      }),
    ).toBe(false)
    expect(
      canStartProcessing({
        summaryBlocked: false,
        transcriptionBlocked: true,
        needsTranscription: false,
      }),
    ).toBe(true)
  })
})
