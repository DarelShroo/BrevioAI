import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import { i18nMessages } from '@/i18n'
import { UI_LOCALES } from '@/i18n/languages'
import {
  categoryLabel,
  formatLabel,
  styleLabel,
  summaryLevelLabel,
} from '@/utils/labels'

const CRITICAL_KEYS = [
  'params.summaryProvider',
  'params.folder',
  'params.folderHint',
  'params.noFolder',
  'files.choose',
  'categories.simple_summary',
  'summaryLevels.concise',
] as const

const ENGLISH_LEFTOVERS =
  /Summary provider|No folder|Choose files|Simple summary|Optional\. Organize|Concise\b/

describe('all UI locales translate critical summary strings', () => {
  for (const locale of UI_LOCALES) {
    if (locale === 'en') continue

    it(`${locale} does not leave dashboard catalog labels in English`, () => {
      const i18n = createI18n({
        legacy: false,
        locale,
        fallbackLocale: 'en',
        messages: i18nMessages,
      })
      const t = i18n.global.t
      const te = i18n.global.te

      for (const key of CRITICAL_KEYS) {
        const value = String(t(key))
        expect(value, `${locale}:${key}`).not.toMatch(ENGLISH_LEFTOVERS)
        expect(value, `${locale}:${key}`).not.toBe(String(t(key, {}, { locale: 'en' })))
      }

      expect(categoryLabel('simple_summary', t, te), locale).not.toBe('Simple summary')
      expect(styleLabel('simple_summary', 'default', t, te), locale).not.toBe('Default')
      expect(summaryLevelLabel('concise', t, te), locale).not.toBe('Concise')
      // formats.text is "Text" in German (same spelling); still require a catalog hit.
      expect(te('formats.text'), locale).toBe(true)
      expect(formatLabel('text', t, te), locale).toBeTruthy()
    })
  }
})
