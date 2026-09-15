import { createI18n } from 'vue-i18n'
import { ar } from '@/i18n/messages/ar'
import { de } from '@/i18n/messages/de'
import { en, type MessageSchema } from '@/i18n/messages/en'
import { es } from '@/i18n/messages/es'
import { fr } from '@/i18n/messages/fr'
import { hi } from '@/i18n/messages/hi'
import { it } from '@/i18n/messages/it'
import { ja } from '@/i18n/messages/ja'
import { ko } from '@/i18n/messages/ko'
import { pt } from '@/i18n/messages/pt'
import { ru } from '@/i18n/messages/ru'
import { zh } from '@/i18n/messages/zh'
import {
  applyDocumentLocale,
  DEFAULT_LOCALE,
  resolveInitialLocale,
  UI_LOCALES,
} from '@/i18n/languages'
import type { UiLocale } from '@/i18n/types'

export const i18nMessages = {
  ar,
  de,
  en,
  es,
  fr,
  hi,
  it,
  ja,
  ko,
  pt,
  ru,
  zh,
} as const satisfies Record<UiLocale, MessageSchema>

export const i18n = createI18n<[MessageSchema], UiLocale, false>({
  legacy: false,
  locale: resolveInitialLocale(UI_LOCALES),
  fallbackLocale: DEFAULT_LOCALE,
  messages: i18nMessages,
  missingWarn: false,
  fallbackWarn: false,
})

applyDocumentLocale(i18n.global.locale.value)
