import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import {
  applyDocumentLocale,
  DEFAULT_LOCALE,
  localesFromBackendLanguages,
  LOCALE_STORAGE_KEY,
  NATIVE_LOCALE_NAMES,
  UI_LOCALES,
} from '@/i18n/languages'
import type { UiLocale } from '@/i18n/types'
import { useCatalogStore } from '@/stores/catalog.store'

export function useI18nLocale() {
  const { locale } = useI18n()
  const catalog = useCatalogStore()
  const { languages, loaded } = storeToRefs(catalog)

  const availableLocales = computed<UiLocale[]>(() => {
    if (!loaded.value || languages.value.length === 0) return [...UI_LOCALES]
    const fromBackend = localesFromBackendLanguages(languages.value)
    return fromBackend.length ? fromBackend : [...UI_LOCALES]
  })

  const localeOptions = computed(() =>
    availableLocales.value.map((code) => ({
      label: NATIVE_LOCALE_NAMES[code],
      value: code,
    })),
  )

  function setLocale(next: UiLocale) {
    const resolved = availableLocales.value.includes(next) ? next : DEFAULT_LOCALE
    locale.value = resolved
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, resolved)
    }
    applyDocumentLocale(resolved)
  }

  function syncWithAvailable() {
    const current = locale.value as UiLocale
    if (!availableLocales.value.includes(current)) {
      setLocale(DEFAULT_LOCALE)
    }
  }

  return {
    locale,
    availableLocales,
    localeOptions,
    setLocale,
    syncWithAvailable,
  }
}
