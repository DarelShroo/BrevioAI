<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import { localeFromBackendLanguage } from '@/i18n/languages'
import { useAuthStore } from '@/stores/auth.store'
import { useCatalogStore } from '@/stores/catalog.store'
import * as credentialsService from '@/services/credentials.service'
import type { SummaryFormParams } from '@/types/brevio'
import {
  categoryLabel,
  humanizeId,
  providerLabel,
  styleLabel,
  summaryLevelLabel,
} from '@/utils/labels'
import { accessHintForModel, isLocalModelId, resolveModelId } from '@/utils/models'

const model = defineModel<SummaryFormParams>({ required: true })
const catalog = useCatalogStore()
const auth = useAuthStore()
const { t, te, locale } = useI18n()
const keyedProviders = ref<Set<string>>(new Set())
const summaryProvider = ref('')

const styleOptions = computed(() =>
  catalog.stylesFor(model.value.category).map((id) => ({
    label: styleLabel(model.value.category, id, t, te),
    value: id,
  })),
)
const languageOptions = computed(() =>
  catalog.languages.map((name) => ({
    label: t(`languages.${name}`),
    value: name,
  })),
)
const providerOptions = computed(() =>
  catalog.providers.map((item) => ({
    label: providerLabel(item.id, t, te),
    value: item.id,
  })),
)
const modelsForProvider = computed(() => {
  const provider = summaryProvider.value
  return catalog.catalog.filter((item) => !provider || item.provider === provider)
})
const modelOptions = computed(() =>
  modelsForProvider.value.map((item) => {
    const base = item.display_name || item.id
    if (item.status === 'deprecated' || item.status === 'preview') {
      return {
        label: `${base} (${humanizeId(item.status)})`,
        value: item.id,
      }
    }
    return { label: base, value: item.id }
  }),
)
const categoryOptions = computed(() =>
  catalog.categories.map((id) => ({
    label: categoryLabel(id, t, te),
    value: id,
  })),
)
const summaryLevelOptions = computed(() =>
  catalog.summaryLevels.map((id) => ({
    label: summaryLevelLabel(id, t, te),
    value: id,
  })),
)
const selectedModelId = computed(() => resolveModelId(model.value.model))
const selectedCatalogModel = computed(() => catalog.modelById(selectedModelId.value))
const parameterIds = computed(() => selectedCatalogModel.value?.parameters || [])
const reasoningValues = computed(() => selectedCatalogModel.value?.reasoning_values || [])
const hasProviderKey = computed(() => {
  const provider = selectedCatalogModel.value?.provider?.trim().toLowerCase()
  return Boolean(provider && keyedProviders.value.has(provider))
})
const accessHint = computed(() => {
  if (isLocalModelId(selectedModelId.value, selectedCatalogModel.value?.provider)) {
    return 'local'
  }
  return accessHintForModel(
    selectedCatalogModel.value,
    hasProviderKey.value,
    auth.profile?.user_credit ?? 0,
  )
})

function defaultLanguage(): string {
  const names = catalog.languages
  if (!names.length) return ''
  const matchingLocale = names.find((name) => localeFromBackendLanguage(name) === locale.value)
  if (matchingLocale) return matchingLocale
  if (names.includes('SPANISH')) return 'SPANISH'
  if (names.includes('ENGLISH')) return 'ENGLISH'
  return names[0]
}

function pickModelForProvider(provider: string): string {
  const models = catalog.catalog.filter((item) => item.provider === provider)
  const recommended = models.find(
    (item) => item.recommended !== false && item.status !== 'deprecated',
  )
  return (recommended || models[0])?.id || ''
}

function syncProviderFromModel() {
  const current = catalog.modelById(resolveModelId(model.value.model))
  if (current?.provider) {
    summaryProvider.value = current.provider
  } else if (!summaryProvider.value && catalog.providers.length) {
    summaryProvider.value = catalog.providers[0].id
  }
}

function clearUnsupportedParams() {
  const params = new Set(parameterIds.value)
  if (!params.has('reasoning_effort') && !params.has('effort')) {
    model.value.reasoning_effort = null
  }
}

async function loadProviderKeys() {
  try {
    const credentials = await credentialsService.listAllCredentials()
    keyedProviders.value = new Set(
      credentials
        .map((item) => item.provider?.trim().toLowerCase())
        .filter((provider): provider is string => Boolean(provider)),
    )
  } catch {
    keyedProviders.value = new Set()
  }
}

onMounted(() => {
  void Promise.all([
    catalog.loadAll(),
    auth.fetchProfile().catch(() => undefined),
    loadProviderKeys(),
  ]).then(() => {
    if (!model.value.language && catalog.languages.length) {
      model.value.language = defaultLanguage()
    }
    if (!resolveModelId(model.value.model) && catalog.models.length) {
      model.value.model = catalog.preferredModelId()
    }
    syncProviderFromModel()
    if (!model.value.category && catalog.categories.length) {
      model.value.category = catalog.categories[0]
    }
    if (!model.value.style && styleOptions.value.length) {
      model.value.style = styleOptions.value[0].value
    }
    // Format is fixed to markdown for now (selector hidden).
    model.value.format = 'markdown'
    if (!model.value.summary_level && catalog.summaryLevels.length) {
      model.value.summary_level =
        catalog.summaryLevels.find((l) => l === 'concise') || catalog.summaryLevels[0]
    }
  })
})

watch(
  () => model.value.model,
  (value) => {
    const id = resolveModelId(value)
    if (id && id !== value) {
      model.value.model = id
    }
    syncProviderFromModel()
    clearUnsupportedParams()
  },
)

watch(parameterIds, () => {
  clearUnsupportedParams()
})

watch(summaryProvider, (provider, previous) => {
  if (!provider || provider === previous) return
  const current = catalog.modelById(resolveModelId(model.value.model))
  if (current?.provider === provider) return
  const next = pickModelForProvider(provider)
  if (next) model.value.model = next
})

watch(
  () => model.value.category,
  (category) => {
    const styles = catalog.stylesFor(category)
    if (styles.length && !styles.includes(model.value.style)) {
      model.value.style = styles[0]
    }
  },
)
</script>

<template>
  <div class="field-grid" data-testid="summary-params">
    <div class="stack">
      <label for="param-language">{{ t('params.language') }}</label>
      <Select
        input-id="param-language"
        v-model="model.language"
        :options="languageOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('params.selectLanguage')"
        filter
        class="w-full"
      />
    </div>
    <div class="stack">
      <label for="param-summary-provider">{{ t('params.summaryProvider') }}</label>
      <Select
        input-id="param-summary-provider"
        v-model="summaryProvider"
        :options="providerOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('params.selectSummaryProvider')"
        class="w-full"
        data-testid="param-summary-provider"
      />
    </div>
    <div class="stack">
      <label for="param-model">{{ t('params.model') }}</label>
      <Select
        input-id="param-model"
        v-model="model.model"
        :options="modelOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('params.selectModel')"
        filter
        class="w-full"
        data-testid="param-model"
      />
      <p v-if="accessHint === 'local'" class="hint">{{ t('params.localModelHint') }}</p>
      <p v-else-if="accessHint === 'byok'" class="hint">{{ t('params.byokHint') }}</p>
      <p v-else-if="accessHint === 'credits'" class="hint">{{ t('params.paidCreditsHint') }}</p>
      <p v-else-if="accessHint === 'blocked'" class="hint hint-warn">{{ t('params.paidBlockedHint') }}</p>
    </div>
    <div
      v-if="parameterIds.includes('reasoning_effort') || parameterIds.includes('effort')"
      class="stack"
    >
      <label for="param-reasoning">{{ t('params.reasoningEffort') }}</label>
      <Select
        input-id="param-reasoning"
        v-model="model.reasoning_effort"
        :options="reasoningValues"
        :placeholder="t('params.selectReasoning')"
        class="w-full"
        data-testid="param-reasoning"
      />
    </div>
    <div class="stack">
      <label for="param-category">{{ t('params.category') }}</label>
      <Select
        input-id="param-category"
        v-model="model.category"
        :options="categoryOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('params.selectCategory')"
        class="w-full"
      />
    </div>
    <div class="stack">
      <label for="param-style">{{ t('params.style') }}</label>
      <Select
        input-id="param-style"
        v-model="model.style"
        :options="styleOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('params.selectStyle')"
        class="w-full"
      />
    </div>
    <div class="stack">
      <label for="param-level">{{ t('params.summaryLevel') }}</label>
      <Select
        input-id="param-level"
        v-model="model.summary_level"
        :options="summaryLevelOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('params.selectLevel')"
        class="w-full"
      />
    </div>
  </div>
</template>

<style scoped>
.w-full {
  width: 100%;
}

.hint {
  margin: 0;
  color: var(--bv-muted, #6b7280);
  font-size: 0.85rem;
}

.hint-warn {
  color: var(--bv-warning, #b45309);
}
</style>
