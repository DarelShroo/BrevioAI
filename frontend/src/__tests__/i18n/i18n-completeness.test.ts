import { describe, expect, it } from 'vitest'
import { i18nMessages } from '@/i18n'
import { UI_LOCALES } from '@/i18n/languages'
import type { UiLocale } from '@/i18n/types'

type NestedRecord = Record<string, unknown>

function getLeafNodes(obj: NestedRecord, prefix = ''): Map<string, string> {
  const leaves = new Map<string, string>()
  for (const [key, val] of Object.entries(obj)) {
    const fullPath = prefix ? `${prefix}.${key}` : key
    if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
      const nestedLeaves = getLeafNodes(val as NestedRecord, fullPath)
      for (const [nestedKey, nestedVal] of nestedLeaves.entries()) {
        leaves.set(nestedKey, nestedVal)
      }
    } else {
      leaves.set(fullPath, String(val))
    }
  }
  return leaves
}

function extractPlaceholders(text: string): string[] {
  const matches = text.match(/\{([a-zA-Z0-9_]+)\}/g)
  if (!matches) return []
  return matches.map((m) => m.slice(1, -1)).sort()
}

describe('i18n Completeness and Placeholder Parity', () => {
  const enLeaves = getLeafNodes(i18nMessages.en as NestedRecord)

  it('en locale has a substantial catalog of keys', () => {
    expect(enLeaves.size).toBeGreaterThan(150)
  })

  for (const locale of UI_LOCALES) {
    if (locale === 'en') continue

    describe(`Locale: ${locale}`, () => {
      const targetLeaves = getLeafNodes(i18nMessages[locale as UiLocale] as NestedRecord)

      it(`contains 100% of keys defined in en`, () => {
        const missingKeys: string[] = []
        for (const [enKey] of enLeaves.entries()) {
          if (!targetLeaves.has(enKey)) {
            missingKeys.push(enKey)
          }
        }
        expect(
          missingKeys,
          `Missing translations in ${locale}: \n${missingKeys.join('\n')}`,
        ).toEqual([])
      })

      it(`has non-empty values for every key`, () => {
        const emptyKeys: string[] = []
        for (const [key, value] of targetLeaves.entries()) {
          if (value.trim().length === 0) {
            emptyKeys.push(key)
          }
        }
        expect(
          emptyKeys,
          `Empty translation keys in ${locale}: \n${emptyKeys.join('\n')}`,
        ).toEqual([])
      })

      it(`preserves required placeholders from en`, () => {
        const placeholderMismatches: string[] = []
        for (const [enKey, enVal] of enLeaves.entries()) {
          const expectedPlaceholders = extractPlaceholders(enVal)
          if (expectedPlaceholders.length === 0) continue

          const targetVal = targetLeaves.get(enKey) || ''
          const actualPlaceholders = extractPlaceholders(targetVal)

          // Check that all expected placeholders exist in actual
          for (const ph of expectedPlaceholders) {
            if (!actualPlaceholders.includes(ph)) {
              placeholderMismatches.push(
                `${enKey}: expected {${ph}} but got "${targetVal}" (en: "${enVal}")`,
              )
            }
          }
        }
        expect(
          placeholderMismatches,
          `Placeholder mismatches in ${locale}:\n${placeholderMismatches.join('\n')}`,
        ).toEqual([])
      })
    })
  }
})
