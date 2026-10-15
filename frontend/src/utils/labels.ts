import { i18n } from '@/i18n'

/** Turn machine ids into readable Title Case when no translation exists. */
export function humanizeId(value: string | null | undefined): string {
  const raw = String(value || '').trim()
  if (!raw) return ''
  return raw
    .replace(/[/\\]+/g, ' ')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .filter(Boolean)
    .map((word) => {
      if (/^[A-Z0-9]{2,}$/.test(word)) return word
      if (/^\d/.test(word)) return word
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    })
    .join(' ')
}

type Translate = (key: string) => string
type TranslateExists = (key: string) => boolean

function resolveTranslate(
  t?: Translate,
  te?: TranslateExists,
): { t: Translate; te: TranslateExists } {
  return {
    t: t || ((key) => String(i18n.global.t(key))),
    te: te || ((key) => i18n.global.te(key)),
  }
}

export function catalogLabel(
  namespace: string,
  id: string | null | undefined,
  t?: Translate,
  te?: TranslateExists,
): string {
  const value = String(id || '').trim()
  if (!value) return ''
  const { t: translate, te: exists } = resolveTranslate(t, te)
  const key = `${namespace}.${value}`
  if (exists(key)) return translate(key)
  return humanizeId(value)
}

export function categoryLabel(
  id: string | null | undefined,
  t?: Translate,
  te?: TranslateExists,
): string {
  return catalogLabel('categories', id, t, te)
}

export function styleLabel(
  category: string | null | undefined,
  style: string | null | undefined,
  t?: Translate,
  te?: TranslateExists,
): string {
  const cat = String(category || '').trim()
  const value = String(style || '').trim()
  if (!value) return ''
  const { t: translate, te: exists } = resolveTranslate(t, te)
  if (cat) {
    const scoped = `styles.${cat}.${value}`
    if (exists(scoped)) return translate(scoped)
  }
  const shared = `styles._.${value}`
  if (exists(shared)) return translate(shared)
  return humanizeId(value)
}

export function formatLabel(
  id: string | null | undefined,
  t?: Translate,
  te?: TranslateExists,
): string {
  return catalogLabel('formats', id, t, te)
}

export function summaryLevelLabel(
  id: string | null | undefined,
  t?: Translate,
  te?: TranslateExists,
): string {
  return catalogLabel('summaryLevels', id, t, te)
}

export function reasoningLevelLabel(
  id: string | null | undefined,
  t?: Translate,
  te?: TranslateExists,
): string {
  return catalogLabel('reasoningLevels', id, t, te)
}

export function providerLabel(
  id: string | null | undefined,
  t?: Translate,
  te?: TranslateExists,
): string {
  return catalogLabel('providers', id, t, te)
}

export function statusLabel(
  id: string | null | undefined,
  t?: Translate,
  te?: TranslateExists,
): string {
  const value = String(id || 'UNKNOWN').trim().toUpperCase()
  const { t: translate, te: exists } = resolveTranslate(t, te)
  const key = `status.${value}`
  if (exists(key)) return translate(key)
  return humanizeId(value)
}
