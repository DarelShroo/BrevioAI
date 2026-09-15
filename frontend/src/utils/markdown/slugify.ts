/**
 * Stable GitHub-like heading IDs that keep international characters.
 * Avoids Unicode property escapes for broader toolchain compatibility.
 */
export function slugifyHeading(raw: string): string {
  const text = raw
    .normalize('NFKC')
    .trim()
    .toLowerCase()
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[!"#$%&'()*+,./:;<=>?@[\\\]^`{|}~]+/g, '')
    .replace(/[\s_]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')

  return text || 'section'
}

export function uniqueSlug(base: string, used: Set<string>): string {
  let slug = base
  let n = 1
  while (used.has(slug)) {
    slug = `${base}-${n}`
    n += 1
  }
  used.add(slug)
  return slug
}
