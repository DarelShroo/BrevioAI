<script setup lang="ts">
import { watch } from 'vue'
import Select from 'primevue/select'
import { ChevronDown } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useI18nLocale } from '@/composables/useI18nLocale'
import type { UiLocale } from '@/i18n/types'

withDefaults(
  defineProps<{
    variant?: 'default' | 'ghost'
  }>(),
  { variant: 'default' },
)

const { t } = useI18n()
const { locale, localeOptions, setLocale, syncWithAvailable } = useI18nLocale()

watch(localeOptions, () => syncWithAvailable(), { immediate: true })

function onChange(value: unknown) {
  if (typeof value === 'string') setLocale(value as UiLocale)
}
</script>

<template>
  <div class="locale-switcher" :class="variant">
    <Select
      :model-value="locale"
      :options="localeOptions"
      option-label="label"
      option-value="value"
      :aria-label="t('locale.label')"
      data-testid="locale-select"
      class="locale-select"
      @update:model-value="onChange"
    >
      <template v-if="variant === 'ghost'" #dropdownicon>
        <ChevronDown :size="16" :stroke-width="2" />
      </template>
    </Select>
  </div>
</template>

<style scoped>
.locale-select {
  min-width: 9.5rem;
}

.ghost .locale-select {
  min-width: 8.5rem;
}

.ghost :deep(.p-select) {
  background: transparent;
  border: 0;
  box-shadow: none;
  color: #334155;
  font-weight: 500;
  padding: 0.35rem 0.55rem;
}

.ghost :deep(.p-select:not(.p-disabled).p-focus) {
  box-shadow: none;
  background: rgb(241 245 249 / 0.8);
}

.ghost :deep(.p-select-label) {
  padding-inline-end: 0.35rem;
}
</style>
