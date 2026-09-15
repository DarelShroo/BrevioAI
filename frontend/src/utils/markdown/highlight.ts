import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import css from 'highlight.js/lib/languages/css'
import go from 'highlight.js/lib/languages/go'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import python from 'highlight.js/lib/languages/python'
import rust from 'highlight.js/lib/languages/rust'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'

let registered = false

const ALIASES: Record<string, string> = {
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  py: 'python',
  sh: 'bash',
  shell: 'bash',
  zsh: 'bash',
  console: 'bash',
  yml: 'yaml',
  html: 'xml',
  htm: 'xml',
  svg: 'xml',
  rs: 'rust',
  golang: 'go',
  cplusplus: 'cpp',
  'c++': 'cpp',
  md: 'markdown',
}

function ensureRegistered(): void {
  if (registered) return
  hljs.registerLanguage('bash', bash)
  hljs.registerLanguage('c', c)
  hljs.registerLanguage('cpp', cpp)
  hljs.registerLanguage('css', css)
  hljs.registerLanguage('go', go)
  hljs.registerLanguage('java', java)
  hljs.registerLanguage('javascript', javascript)
  hljs.registerLanguage('json', json)
  hljs.registerLanguage('markdown', markdown)
  hljs.registerLanguage('python', python)
  hljs.registerLanguage('rust', rust)
  hljs.registerLanguage('sql', sql)
  hljs.registerLanguage('typescript', typescript)
  hljs.registerLanguage('xml', xml)
  hljs.registerLanguage('yaml', yaml)
  registered = true
}

export function normalizeLanguage(lang?: string | null): string {
  if (!lang) return ''
  const key = lang.trim().toLowerCase()
  return ALIASES[key] || key
}

export function highlightCode(code: string, lang?: string | null): { html: string; language: string } {
  ensureRegistered()
  const language = normalizeLanguage(lang)
  if (language && hljs.getLanguage(language)) {
    try {
      return {
        html: hljs.highlight(code, { language, ignoreIllegals: true }).value,
        language,
      }
    } catch {
      // fall through
    }
  }
  try {
    const auto = hljs.highlightAuto(code)
    return { html: auto.value, language: language || auto.language || '' }
  } catch {
    return { html: hljs.highlightAuto(code).value, language }
  }
}

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
