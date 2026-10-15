import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function getFilesRecursively(dir: string, extension: string): string[] {
  let results: string[] = []
  const list = fs.readdirSync(dir)
  for (const file of list) {
    const filePath = path.join(dir, file)
    const stat = fs.statSync(filePath)
    if (stat && stat.isDirectory()) {
      results = results.concat(getFilesRecursively(filePath, extension))
    } else if (filePath.endsWith(extension)) {
      results.push(filePath)
    }
  }
  return results
}

describe('Anti-Hardcode Frontend Static Audit', () => {
  const srcDir = path.resolve(__dirname, '../../')
  const vueFiles = getFilesRecursively(srcDir, '.vue')

  it('scanned all Vue components in src', () => {
    expect(vueFiles.length).toBeGreaterThan(10)
  })

  it('has no hardcoded user-facing attributes (placeholder, aria-label, alt) without dynamic i18n binding', () => {
    // Only match attributes that are NOT prefixed by : or v-bind: (preceded by whitespace)
    const attributeRegex = /(?<=\s)(placeholder|aria-label|alt)\s*=\s*"([^"]+)"/g
    const violations: string[] = []

    for (const file of vueFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      const relativePath = path.relative(srcDir, file)

      let match: RegExpExecArray | null
      while ((match = attributeRegex.exec(content)) !== null) {
        const attr = match[1]
        const val = match[2].trim()

        // Skip empty alt (for decorative images aria-hidden), URLs, technical IDs
        if (
          val === '' ||
          val.startsWith('http') ||
          val.startsWith('#') ||
          val.startsWith('/') ||
          val.includes('{{') ||
          (/^[a-z0-9_-]+$/i.test(val) && (val.length <= 3 || val.includes('_') || val.includes('-'))) ||
          /^[0-9]+$/.test(val)
        ) {
          continue
        }

        violations.push(`${relativePath}: hardcoded ${attr}="${val}"`)
      }
    }

    expect(
      violations,
      `Found hardcoded attributes that should use :${violations[0]?.split(':')[1]?.trim() || 'attr'}:\n${violations.join('\n')}`,
    ).toEqual([])
  })

  it('ensures no silent fallback patterns like `translations.get(key, key)` or empty string fallbacks mask missing translations in source code', () => {
    const tsFiles = getFilesRecursively(srcDir, '.ts').filter((f) => !f.includes('__tests__'))
    const silentFallbackRegex = /translations?\.get\([^,]+,\s*(?:key|["']Error["']|["']Something went wrong["'])\)/g
    const violations: string[] = []

    for (const file of tsFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      const relativePath = path.relative(srcDir, file)

      if (silentFallbackRegex.test(content)) {
        violations.push(`${relativePath}: silent fallback detected`)
      }
    }

    expect(violations).toEqual([])
  })
})
