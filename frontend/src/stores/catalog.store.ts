import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { uniquePromptLanguages } from '@/i18n/languages'
import { i18n } from '@/i18n'
import * as brevioService from '@/services/brevio.service'
import type { CategoryStylesMap, TranscriptionModel, TranscriptionProvider } from '@/types/brevio'
import type { CatalogModel, CatalogProvider, ModelOptionGroup } from '@/utils/models'
import { defaultModelId, modelGroups, resolveModelId } from '@/utils/models'

import { parseApiError } from '@/utils/errors'

export const useCatalogStore = defineStore('catalog', () => {
  const languages = ref<string[]>([])
  const catalog = ref<CatalogModel[]>([])
  const providers = ref<CatalogProvider[]>([])
  const categoryStyles = ref<CategoryStylesMap>({})
  const formats = ref<string[]>([])
  const summaryLevels = ref<string[]>([])
  const transcriptionProviders = ref<TranscriptionProvider[]>([])
  const transcriptionModels = ref<TranscriptionModel[]>([])
  const transcriptionEnvironment = ref<string>('')
  const defaultTranscriptionProvider = ref<string | null>(null)
  const defaultTranscriptionModel = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loaded = ref(false)

  const models = computed(() => catalog.value.map((item) => item.id))
  const localModels = computed(() => catalog.value.filter((item) => item.access === 'local'))
  const paidModels = computed(() => catalog.value.filter((item) => item.access === 'pay_per_use'))
  const paidProviders = computed(() =>
    providers.value.filter((item) => item.requires_api_key && item.access === 'pay_per_use'),
  )
  const selectableTranscriptionProviders = computed(() =>
    transcriptionProviders.value.filter((item) => item.user_access),
  )
  const selectableTranscriptionModels = computed(() =>
    transcriptionModels.value.filter((item) => item.user_access),
  )
  const groupedModels = computed<ModelOptionGroup[]>(() => modelGroups(catalog.value))
  const categories = computed(() => Object.keys(categoryStyles.value))

  function stylesFor(category: string): string[] {
    return (categoryStyles.value[category] || []).map((item) => item.style)
  }

  function modelById(id: unknown): CatalogModel | undefined {
    const resolved = resolveModelId(id)
    return catalog.value.find((item) => item.id === resolved)
  }

  function preferredModelId(): string {
    return defaultModelId(catalog.value)
  }

  async function loadAll(force = false) {
    if (loaded.value && !force) return
    loading.value = true
    error.value = null
    try {
      const [langs, modelPayload, combos, fmts, levels, transcription] = await Promise.all([
        brevioService.fetchLanguages(),
        brevioService.fetchModels(),
        brevioService.fetchCategoryStyles(),
        brevioService.fetchOutputFormats(),
        brevioService.fetchSummaryLevels(),
        brevioService.fetchTranscriptionProviders(),
      ])
      languages.value = uniquePromptLanguages(langs)
      catalog.value = modelPayload.catalog
      providers.value = modelPayload.providers
      categoryStyles.value = combos
      formats.value = fmts
      summaryLevels.value = levels
      transcriptionProviders.value = transcription.providers || []
      transcriptionModels.value = transcription.models || []
      transcriptionEnvironment.value = transcription.environment || ''
      defaultTranscriptionProvider.value = transcription.default || null
      defaultTranscriptionModel.value = transcription.default_model || null
      loaded.value = true
    } catch (err) {
      error.value = parseApiError(err, String(i18n.global.t('errors.loadCatalogs')))
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    languages,
    models,
    catalog,
    providers,
    localModels,
    paidModels,
    paidProviders,
    groupedModels,
    categoryStyles,
    formats,
    summaryLevels,
    transcriptionProviders,
    transcriptionModels,
    transcriptionEnvironment,
    selectableTranscriptionProviders,
    selectableTranscriptionModels,
    defaultTranscriptionProvider,
    defaultTranscriptionModel,
    loading,
    error,
    loaded,
    categories,
    stylesFor,
    modelById,
    preferredModelId,
    loadAll,
  }
})
