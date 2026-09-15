import type { CatalogModel } from '@/utils/models'
import { accessHintForModel } from '@/utils/models'

export interface TranscriptionAccessProvider {
  id: string
  requires_api_key: boolean
}

export function isSummaryModelBlocked(
  model: CatalogModel | undefined,
  keyedProviders: Set<string>,
  credits: number,
): boolean {
  if (!model) return false
  const provider = model.provider?.trim().toLowerCase() || ''
  const hint = accessHintForModel(model, Boolean(provider && keyedProviders.has(provider)), credits)
  return hint === 'blocked'
}

export function isTranscriptionKeyMissing(
  provider: TranscriptionAccessProvider | undefined,
  keyedProviders: Set<string>,
): boolean {
  if (!provider?.requires_api_key) return false
  return !keyedProviders.has(provider.id.trim().toLowerCase())
}

export function canStartProcessing(options: {
  summaryBlocked: boolean
  transcriptionBlocked: boolean
  needsTranscription: boolean
}): boolean {
  if (options.summaryBlocked) return false
  if (options.needsTranscription && options.transcriptionBlocked) return false
  return true
}
