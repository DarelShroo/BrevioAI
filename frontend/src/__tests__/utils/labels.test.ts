import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import { en } from '@/i18n/messages/en'
import { es } from '@/i18n/messages/es'
import {
  categoryLabel,
  humanizeId,
  providerLabel,
  styleLabel,
  summaryLevelLabel,
} from '@/utils/labels'

describe('labels helpers', () => {
  it('humanizes snake_case and kebab-case ids', () => {
    expect(humanizeId('simple_summary')).toBe('Simple Summary')
    expect(humanizeId('quick_ref')).toBe('Quick Ref')
    expect(humanizeId('gpt-transcribe')).toBe('Gpt Transcribe')
    expect(humanizeId('local_whisper')).toBe('Local Whisper')
  })

  it('resolves Spanish catalog labels from i18n', () => {
    const i18n = createI18n({
      legacy: false,
      locale: 'es',
      messages: { es, en },
    })
    const t = i18n.global.t
    const te = i18n.global.te
    expect(categoryLabel('simple_summary', t, te)).toBe('Resumen simple')
    expect(styleLabel('education', 'quick_ref', t, te)).toBe('Referencia rápida')
    expect(summaryLevelLabel('very_concise', t, te)).toBe('Muy conciso')
    expect(providerLabel('openai', t, te)).toBe('OpenAI')
  })

  it('falls back to humanized text when a key is missing', () => {
    const i18n = createI18n({
      legacy: false,
      locale: 'en',
      messages: { en },
    })
    expect(categoryLabel('brand_new_category', i18n.global.t, i18n.global.te)).toBe(
      'Brand New Category',
    )
  })
})
