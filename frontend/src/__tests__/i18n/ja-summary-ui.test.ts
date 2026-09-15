import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import { en } from '@/i18n/messages/en'
import { ja } from '@/i18n/messages/ja'
import { categoryLabel, styleLabel, summaryLevelLabel } from '@/utils/labels'

const REQUIRED_JA = [
  'params.summaryProvider',
  'params.folder',
  'params.folderHint',
  'params.noFolder',
  'files.choose',
  'categories.simple_summary',
  'styles.simple_summary.default',
  'summaryLevels.concise',
  'formats.text',
]

describe('japanese locale completeness for summary UI', () => {
  it('translates the dashboard strings that were previously English leftovers', () => {
    const i18n = createI18n({
      legacy: false,
      locale: 'ja',
      fallbackLocale: 'en',
      messages: { ja, en },
    })
    for (const key of REQUIRED_JA) {
      const value = String(i18n.global.t(key))
      expect(value, key).not.toEqual(String(i18n.global.t(key, {}, { locale: 'en' })))
      expect(value, key).not.toMatch(/Summary provider|No folder|Choose files|Simple summary|Optional/)
    }
    expect(categoryLabel('simple_summary', i18n.global.t, i18n.global.te)).toBe('簡易要約')
    expect(styleLabel('simple_summary', 'default', i18n.global.t, i18n.global.te)).toBe('標準')
    expect(summaryLevelLabel('concise', i18n.global.t, i18n.global.te)).toBe('簡潔')
  })
})
