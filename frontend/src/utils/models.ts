export type ModelAccess = 'local' | 'pay_per_use'
export type ModelAccessHint = 'local' | 'byok' | 'credits' | 'blocked'

export interface CatalogModel {
  id: string
  provider: string
  access: ModelAccess
  requires_api_key: boolean
  display_name: string
  output_token_param?: string
  parameters?: string[]
  reasoning?: string | null
  reasoning_values?: string[]
  status?: string
  retirement?: string | null
  recommended?: boolean
}

export interface CatalogProvider {
  id: string
  access: ModelAccess
  requires_api_key: boolean
}

export interface ModelsCatalogPayload {
  models: string[]
  catalog: CatalogModel[]
  providers: CatalogProvider[]
  environment?: string
}

export interface ModelOptionGroup {
  labelKey: 'params.localModels' | 'params.paidModels'
  access: ModelAccess
  items: Array<{ label: string; value: string }>
}

const LOCAL_MODEL_IDS = new Set([
  'qwen3:8b',
  'qwen3:14b',
  'qwen3:14b-q6',
  'qwen3:32b',
  'gpt-oss:20b',
  'deepseek-r1-local:iq3-xs',
  'batiai/gemma4-31b:iq3',
])

export function resolveModelId(value: unknown): string {
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  if (value && typeof value === 'object') {
    const typed = value as { value?: unknown; id?: unknown }
    if (typeof typed.value === 'string') return typed.value.trim()
    if (typeof typed.id === 'string') return typed.id.trim()
  }
  return ''
}

export function isLocalModelId(id: string, provider?: string): boolean {
  const modelId = resolveModelId(id)
  if (!modelId) return false
  if ((provider || '').trim().toLowerCase() === 'ollama') return true
  if (LOCAL_MODEL_IDS.has(modelId)) return true
  return modelId.includes(':')
}

export function inferModelAccess(id: string, provider?: string): ModelAccess {
  return isLocalModelId(id, provider) ? 'local' : 'pay_per_use'
}

function asCatalogModel(item: unknown): CatalogModel | null {
  if (typeof item === 'string' && item.trim()) {
    const id = item.trim()
    const access = inferModelAccess(id)
    return {
      id,
      provider: access === 'local' ? 'ollama' : 'unknown',
      access,
      requires_api_key: access === 'pay_per_use',
      display_name: id,
    }
  }
  if (!item || typeof item !== 'object') return null
  const typed = item as Partial<CatalogModel> & Record<string, unknown>
  if (!typed.id) return null
  const access: ModelAccess =
    typed.access === 'local' || isLocalModelId(typed.id, typed.provider)
      ? 'local'
      : 'pay_per_use'
  // Ignore backend-only limits if a stale payload includes them.
  return {
    id: typed.id,
    provider: typed.provider || (access === 'local' ? 'ollama' : 'unknown'),
    access,
    requires_api_key: access === 'pay_per_use',
    display_name: typed.display_name || typed.id,
    output_token_param: typed.output_token_param,
    parameters: Array.isArray(typed.parameters)
      ? typed.parameters.filter(
          (id) => id !== 'max_output_tokens' && id !== 'temperature' && id !== 'context_window',
        )
      : undefined,
    reasoning: typed.reasoning,
    reasoning_values: Array.isArray(typed.reasoning_values) ? typed.reasoning_values : undefined,
    status: typed.status,
    retirement: typed.retirement,
    recommended: typed.recommended,
  }
}

function uniqueProviders(catalog: CatalogModel[]): CatalogProvider[] {
  const seen = new Map<string, CatalogProvider>()
  for (const model of catalog) {
    if (seen.has(model.provider)) continue
    seen.set(model.provider, {
      id: model.provider,
      access: model.access,
      requires_api_key: model.requires_api_key,
    })
  }
  return [...seen.values()].sort((a, b) => {
    if (a.access !== b.access) return a.access === 'local' ? -1 : 1
    return a.id.localeCompare(b.id)
  })
}

export function normalizeModelsPayload(data: unknown): ModelsCatalogPayload {
  if (Array.isArray(data)) {
    const catalog = data.map(asCatalogModel).filter((item): item is CatalogModel => item !== null)
    return {
      models: catalog.map((item) => item.id),
      catalog,
      providers: uniqueProviders(catalog),
    }
  }
  if (!data || typeof data !== 'object') {
    return { models: [], catalog: [], providers: [] }
  }
  const typed = data as {
    models?: unknown
    catalog?: unknown
    providers?: unknown
    environment?: unknown
  }
  const fromCatalog = Array.isArray(typed.catalog)
    ? typed.catalog.map(asCatalogModel).filter((item): item is CatalogModel => item !== null)
    : []
  const fromModels = Array.isArray(typed.models)
    ? typed.models.map(asCatalogModel).filter((item): item is CatalogModel => item !== null)
    : []
  const catalog = fromCatalog.length ? fromCatalog : fromModels
  const providers = Array.isArray(typed.providers)
    ? typed.providers
        .map((item) => {
          if (!item || typeof item !== 'object' || !('id' in item)) return null
          const provider = item as Partial<CatalogProvider>
          if (!provider.id) return null
          const access: ModelAccess =
            provider.access === 'local' || provider.id.toLowerCase() === 'ollama'
              ? 'local'
              : 'pay_per_use'
          return {
            id: provider.id,
            access,
            requires_api_key: access === 'pay_per_use',
          } satisfies CatalogProvider
        })
        .filter((item): item is CatalogProvider => item !== null)
    : uniqueProviders(catalog)

  return {
    models: catalog.map((item) => item.id),
    catalog,
    providers: providers.length ? providers : uniqueProviders(catalog),
    environment: typeof typed.environment === 'string' ? typed.environment : undefined,
  }
}

export function defaultModelId(catalog: CatalogModel[]): string {
  const recommendedLocal = catalog.find(
    (item) => item.access === 'local' && item.recommended !== false && item.status !== 'deprecated',
  )
  if (recommendedLocal) return recommendedLocal.id
  const local = catalog.find((item) => item.access === 'local')
  const recommendedPaid = catalog.find(
    (item) => item.access === 'pay_per_use' && item.recommended !== false && item.status !== 'deprecated',
  )
  return (recommendedLocal || local || recommendedPaid || catalog[0])?.id || ''
}

export function modelGroups(catalog: CatalogModel[]): ModelOptionGroup[] {
  const local = catalog.filter((item) => item.access === 'local')
  const paid = catalog.filter((item) => item.access === 'pay_per_use')
  const groups: ModelOptionGroup[] = []
  if (local.length) {
    groups.push({
      labelKey: 'params.localModels',
      access: 'local',
      items: local.map((item) => ({ label: item.display_name, value: item.id })),
    })
  }
  if (paid.length) {
    groups.push({
      labelKey: 'params.paidModels',
      access: 'pay_per_use',
      items: paid.map((item) => ({
        label: item.status === 'deprecated' ? `${item.display_name} (deprecated)` : item.display_name,
        value: item.id,
      })),
    })
  }
  return groups
}

export function accessHintForModel(
  model: CatalogModel | undefined,
  hasProviderKey: boolean,
  credits: number,
): ModelAccessHint | null {
  if (!model) return null
  if (
    model.access === 'local' ||
    !model.requires_api_key ||
    isLocalModelId(model.id, model.provider)
  ) {
    return 'local'
  }
  if (hasProviderKey) return 'byok'
  if (credits > 0) return 'credits'
  return 'blocked'
}
