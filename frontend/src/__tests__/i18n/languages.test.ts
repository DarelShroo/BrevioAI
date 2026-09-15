import { describe, expect, it } from 'vitest'
import {
  BACKEND_PROMPT_LANGUAGES,
  filterPromptLanguages,
  localeFromBackendLanguage,
  localesFromBackendLanguages,
  uniquePromptLanguages,
  UI_LOCALES,
} from '@/i18n/languages'
import { i18nMessages } from '@/i18n'

describe('backend-aligned i18n locales', () => {
  it('ships UI messages only for backend prompt languages', () => {
    const messageLocales = Object.keys(i18nMessages).sort()
    expect(messageLocales).toEqual([...UI_LOCALES].sort())
    for (const locale of UI_LOCALES) {
      expect(BACKEND_PROMPT_LANGUAGES.some((name) => localeFromBackendLanguage(name) === locale)).toBe(
        true,
      )
    }
  })

  it('drops backend languages without prompt implementations', () => {
    expect(filterPromptLanguages(['ENGLISH', 'AFRIKAANS', 'SPANISH', 'ZULU'])).toEqual([
      'ENGLISH',
      'SPANISH',
    ])
  })

  it('keeps one canonical language per UI locale', () => {
    expect(
      uniquePromptLanguages([
        'ENGLISH',
        'CHINESE_TRADITIONAL',
        'CHINESE',
        'PORTUGUESE_PORTUGAL',
        'PORTUGUESE_BRAZIL',
        'AFRIKAANS',
      ]),
    ).toEqual(['ENGLISH', 'PORTUGUESE_BRAZIL', 'CHINESE'])
  })

  it('maps catalog languages to UI locales', () => {
    expect(localesFromBackendLanguages(['SPANISH', 'GERMAN', 'ZULU'])).toEqual(['es', 'de'])
  })
})
