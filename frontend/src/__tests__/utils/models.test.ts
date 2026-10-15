import { describe, expect, it } from 'vitest'
import {
  accessHintForModel,
  defaultModelId,
  isLocalModelId,
  modelGroups,
  normalizeModelsPayload,
  resolveModelId,
  type CatalogModel,
} from '@/utils/models'

const local: CatalogModel = {
  id: 'qwen3:8b',
  provider: 'ollama',
  access: 'local',
  requires_api_key: false,
  display_name: 'qwen3:8b',
}

const paid: CatalogModel = {
  id: 'gpt-4o-mini',
  provider: 'openai',
  access: 'pay_per_use',
  requires_api_key: true,
  display_name: 'gpt-4o-mini',
}

describe('model catalog helpers', () => {
  it('normalizes legacy string lists and grouped catalog payloads', () => {
    expect(normalizeModelsPayload(['gpt-4o-mini']).catalog[0]).toMatchObject({
      id: 'gpt-4o-mini',
      access: 'pay_per_use',
      requires_api_key: true,
    })
    expect(normalizeModelsPayload(['qwen3:8b', 'gpt-oss:20b']).catalog).toEqual([
      expect.objectContaining({ id: 'qwen3:8b', access: 'local', requires_api_key: false, provider: 'ollama' }),
      expect.objectContaining({ id: 'gpt-oss:20b', access: 'local', requires_api_key: false }),
    ])

    const grouped = normalizeModelsPayload({
      models: ['qwen3:8b', 'gpt-4o-mini'],
      catalog: [local, paid],
      providers: [
        { id: 'ollama', access: 'local', requires_api_key: false },
        { id: 'openai', access: 'pay_per_use', requires_api_key: true },
      ],
    })
    expect(grouped.catalog).toEqual([local, paid])
    expect(grouped.providers.map((item) => item.id)).toEqual(['ollama', 'openai'])
  })

  it('keeps backend parameter metadata for the selected model', () => {
    const payload = normalizeModelsPayload({
      models: ['gpt-5.6'],
      catalog: [
        {
          id: 'gpt-5.6',
          provider: 'openai',
          access: 'pay_per_use',
          requires_api_key: true,
          display_name: 'gpt-5.6',
          summary_max_output_tokens: 16384,
          context_window: 1_050_000,
          parameters: ['max_output_tokens', 'temperature', 'reasoning_effort'],
          reasoning: 'reasoning_effort',
          reasoning_values: ['none', 'low', 'medium', 'high', 'xhigh', 'max'],
          status: 'stable',
          recommended: true,
        },
      ],
      providers: [{ id: 'openai', access: 'pay_per_use', requires_api_key: true }],
    })
    expect(payload.catalog[0].parameters).toEqual(['reasoning_effort'])
    expect(payload.catalog[0]).not.toHaveProperty('summary_max_output_tokens')
    expect(payload.catalog[0]).not.toHaveProperty('context_window')
    expect(payload.catalog[0].reasoning_values).toEqual([
      'none',
      'low',
      'medium',
      'high',
      'xhigh',
      'max',
    ])
  })
  it('defaults to a local model and groups local vs pay-per-use', () => {
    expect(defaultModelId([paid, local])).toBe('qwen3:8b')
    expect(modelGroups([local, paid])).toEqual([
      {
        labelKey: 'params.localModels',
        access: 'local',
        items: [{ label: 'qwen3:8b', value: 'qwen3:8b' }],
      },
      {
        labelKey: 'params.paidModels',
        access: 'pay_per_use',
        items: [{ label: 'gpt-4o-mini', value: 'gpt-4o-mini' }],
      },
    ])
  })

  it('unwraps select values and picks the correct access hint', () => {
    expect(resolveModelId({ label: 'qwen3:8b', value: 'qwen3:8b' })).toBe('qwen3:8b')
    expect(isLocalModelId('qwen3:8b')).toBe(true)
    expect(isLocalModelId('gpt-4o-mini')).toBe(false)
    const providerWithKey = { id: 'openai', access: 'pay_per_use' as const, requires_api_key: true, has_platform_credential: true }
    const providerWithoutKey = { id: 'openai', access: 'pay_per_use' as const, requires_api_key: true, has_platform_credential: false }
    expect(accessHintForModel(local, false, undefined)).toBe('local')
    expect(accessHintForModel(paid, true, undefined)).toBe('byok')
    expect(accessHintForModel(paid, false, providerWithKey)).toBe('credits')
    expect(accessHintForModel(paid, false, providerWithoutKey)).toBe('blocked')
    expect(
      accessHintForModel(
        {
          ...local,
          access: 'pay_per_use',
          requires_api_key: true,
          provider: 'unknown',
        },
        false,
        undefined,
      ),
    ).toBe('local')
  })

  it('does not treat ollama-style ids as pay-per-use when the catalog is a string list', () => {
    const catalog = normalizeModelsPayload(['qwen3:8b', 'gpt-4o-mini']).catalog
    expect(accessHintForModel(catalog[0], false, undefined)).toBe('local')
    expect(accessHintForModel(catalog[1], false, undefined)).toBe('blocked')
  })
})
