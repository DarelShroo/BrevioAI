import type { UiLocale } from '@/i18n/types'

export const LOCALE_STORAGE_KEY = 'brevio_locale'
export const DEFAULT_LOCALE: UiLocale = 'en'
export const RTL_LOCALES = new Set<UiLocale>(['ar'])

/**
 * Backend LanguageType names that have prompt implementations.
 * Must stay aligned with core.brevio.services.advanced_content_generator.PROMPT_LANGUAGES.
 */
export const BACKEND_PROMPT_LANGUAGES = [
  'ARABIC',
  'ENGLISH',
  'CHINESE',
  'CHINESE_SIMPLIFIED',
  'CHINESE_TRADITIONAL',
  'SPANISH',
  'FRENCH',
  'GERMAN',
  'HINDI',
  'ITALIAN',
  'JAPANESE',
  'KOREAN',
  'PORTUGUESE_PORTUGAL',
  'PORTUGUESE_BRAZIL',
  'RUSSIAN',
] as const

export type BackendPromptLanguage = (typeof BACKEND_PROMPT_LANGUAGES)[number]

export const BACKEND_LANGUAGE_TO_LOCALE: Record<BackendPromptLanguage, UiLocale> = {
  ARABIC: 'ar',
  ENGLISH: 'en',
  CHINESE: 'zh',
  CHINESE_SIMPLIFIED: 'zh',
  CHINESE_TRADITIONAL: 'zh',
  SPANISH: 'es',
  FRENCH: 'fr',
  GERMAN: 'de',
  HINDI: 'hi',
  ITALIAN: 'it',
  JAPANESE: 'ja',
  KOREAN: 'ko',
  PORTUGUESE_PORTUGAL: 'pt',
  PORTUGUESE_BRAZIL: 'pt',
  RUSSIAN: 'ru',
}

export const UI_LOCALES: readonly UiLocale[] = [
  'en',
  'es',
  'pt',
  'fr',
  'de',
  'it',
  'ru',
  'zh',
  'ja',
  'ko',
  'ar',
  'hi',
] as const

const CANONICAL_BACKEND_BY_LOCALE: Record<UiLocale, readonly BackendPromptLanguage[]> = {
  ar: ['ARABIC'],
  en: ['ENGLISH'],
  zh: ['CHINESE', 'CHINESE_SIMPLIFIED', 'CHINESE_TRADITIONAL'],
  es: ['SPANISH'],
  fr: ['FRENCH'],
  de: ['GERMAN'],
  hi: ['HINDI'],
  it: ['ITALIAN'],
  ja: ['JAPANESE'],
  ko: ['KOREAN'],
  pt: ['PORTUGUESE_BRAZIL', 'PORTUGUESE_PORTUGAL'],
  ru: ['RUSSIAN'],
}

export const NATIVE_LOCALE_NAMES: Record<UiLocale, string> = {
  ar: 'العربية',
  de: 'Deutsch',
  en: 'English',
  es: 'Español',
  fr: 'Français',
  hi: 'हिन्दी',
  it: 'Italiano',
  ja: '日本語',
  ko: '한국어',
  pt: 'Português',
  ru: 'Русский',
  zh: '中文',
}

const PROMPT_LANGUAGE_SET = new Set<string>(BACKEND_PROMPT_LANGUAGES)

export function isBackendPromptLanguage(name: string): name is BackendPromptLanguage {
  return PROMPT_LANGUAGE_SET.has(name)
}

export function isUiLocale(value: string): value is UiLocale {
  return (UI_LOCALES as readonly string[]).includes(value)
}

export function localeFromBackendLanguage(name: string): UiLocale | null {
  if (!isBackendPromptLanguage(name)) return null
  return BACKEND_LANGUAGE_TO_LOCALE[name]
}

export function filterPromptLanguages(backendNames: string[]): string[] {
  return backendNames.filter(isBackendPromptLanguage)
}

export function uniquePromptLanguages(backendNames: string[]): BackendPromptLanguage[] {
  const available = new Set(backendNames)
  const result: BackendPromptLanguage[] = []
  for (const locale of UI_LOCALES) {
    const match = CANONICAL_BACKEND_BY_LOCALE[locale].find((name) => available.has(name))
    if (match) result.push(match)
  }
  return result
}

export function localesFromBackendLanguages(backendNames: string[]): UiLocale[] {
  const unique = uniquePromptLanguages(backendNames)
  const locales = unique.map((name) => BACKEND_LANGUAGE_TO_LOCALE[name])
  return UI_LOCALES.filter((locale) => locales.includes(locale))
}

export function resolveInitialLocale(available: readonly UiLocale[] = UI_LOCALES): UiLocale {
  if (typeof window !== 'undefined') {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY)
    if (stored && isUiLocale(stored) && available.includes(stored)) return stored
  }
  return available.includes(DEFAULT_LOCALE) ? DEFAULT_LOCALE : (available[0] ?? DEFAULT_LOCALE)
}

export function applyDocumentLocale(locale: UiLocale): void {
  if (typeof document === 'undefined') return
  document.documentElement.lang = locale
  document.documentElement.dir = RTL_LOCALES.has(locale) ? 'rtl' : 'ltr'
}
