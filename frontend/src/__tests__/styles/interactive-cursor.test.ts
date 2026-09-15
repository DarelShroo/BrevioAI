import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

describe('interactive cursor contract', () => {
  const css = readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), '../../assets/styles/main.css'),
    'utf8',
  )

  it('sets a global pointer baseline for clickable controls', () => {
    expect(css).toContain('cursor: pointer')
    expect(css).toContain('button:not(:disabled):not([aria-disabled=\'true\'])')
    expect(css).toContain('a[href]')
    expect(css).toContain('.p-password-toggle-mask-icon')
    expect(css).toContain('.job-event-toast')
  })

  it('does not force pointer on disabled controls', () => {
    expect(css).toContain('cursor: not-allowed')
    expect(css).toContain('button:disabled')
  })
})
