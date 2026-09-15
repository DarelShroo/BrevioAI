import MarkdownIt from 'markdown-it'
import type Token from 'markdown-it/lib/token.mjs'
import anchor from 'markdown-it-anchor'
import taskLists from 'markdown-it-task-lists'
import DOMPurify from 'dompurify'
import { escapeHtml, highlightCode } from '@/utils/markdown/highlight'
import { slugifyHeading } from '@/utils/markdown/slugify'

type MarkdownRenderer = InstanceType<typeof MarkdownIt>

export type TocItem = {
  id: string
  level: number
  text: string
}

export type RenderMarkdownResult = {
  html: string
  toc: TocItem[]
}

const ALLOWED_TAGS = [
  'a',
  'abbr',
  'b',
  'blockquote',
  'br',
  'button',
  'code',
  'del',
  'div',
  'em',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'hr',
  'i',
  'img',
  'input',
  'li',
  'ol',
  'p',
  'pre',
  's',
  'span',
  'strong',
  'sub',
  'sup',
  'table',
  'tbody',
  'td',
  'th',
  'thead',
  'tr',
  'ul',
]

const ALLOWED_ATTR = [
  'alt',
  'aria-hidden',
  'aria-label',
  'checked',
  'class',
  'colspan',
  'data-copied-label',
  'data-copy-label',
  'data-lang',
  'disabled',
  'href',
  'id',
  'loading',
  'rel',
  'role',
  'rowspan',
  'src',
  'target',
  'title',
  'type',
]

let purifyHooksInstalled = false

function installPurifyHooks(): void {
  if (purifyHooksInstalled || typeof window === 'undefined') return
  purifyHooksInstalled = true

  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (!(node instanceof Element)) return

    if (node.tagName === 'A') {
      const href = node.getAttribute('href') || ''
      if (/^\s*(javascript|vbscript|data):/i.test(href)) {
        node.removeAttribute('href')
      } else if (/^https?:\/\//i.test(href) || href.startsWith('//')) {
        node.setAttribute('target', '_blank')
        node.setAttribute('rel', 'noopener noreferrer')
      } else if (href.startsWith('#')) {
        node.removeAttribute('target')
      }
    }

    if (node.tagName === 'IMG') {
      const src = node.getAttribute('src') || ''
      if (/^\s*(javascript|vbscript|data:(?!image\/))/i.test(src)) {
        node.removeAttribute('src')
      }
      node.setAttribute('loading', 'lazy')
      if (!node.getAttribute('alt')) node.setAttribute('alt', '')
    }

    if (node.tagName === 'INPUT') {
      const type = (node.getAttribute('type') || '').toLowerCase()
      if (type !== 'checkbox') {
        node.remove()
        return
      }
      node.setAttribute('disabled', '')
      node.setAttribute('type', 'checkbox')
    }
  })
}

function renderCodeBlock(code: string, langHint: string): string {
  const { html, language } = highlightCode(code, langHint)
  const label = language || langHint || ''
  const langAttr = label ? ` data-lang="${escapeHtml(label)}"` : ''
  const langBadge = label
    ? `<span class="md-code__lang">${escapeHtml(label)}</span>`
    : '<span class="md-code__lang" aria-hidden="true"></span>'

  return [
    `<div class="md-code"${langAttr}>`,
    `<div class="md-code__toolbar">`,
    langBadge,
    `<button type="button" class="md-code__copy" data-copy-label="Copy" data-copied-label="Copied" aria-label="Copy code">Copy</button>`,
    `</div>`,
    `<pre class="md-code__pre"><code class="hljs${label ? ` language-${escapeHtml(label)}` : ''}">${html}</code></pre>`,
    `</div>`,
  ].join('')
}

function createMarkdownIt(toc: TocItem[]): MarkdownRenderer {
  const md = new MarkdownIt({
    html: false,
    linkify: true,
    typographer: true,
    breaks: false,
  })

  md.enable(['table', 'strikethrough'])
  md.use(taskLists, { enabled: false, label: true, labelAfter: false })
  md.use(anchor, {
    level: [1, 2, 3, 4, 5, 6],
    slugify: slugifyHeading,
    callback(token: Token, { slug, title }: { slug: string; title: string }) {
      const level = Number(String(token.tag || 'h2').replace('h', '') || 2)
      toc.push({
        id: slug,
        level: Number.isFinite(level) ? level : 2,
        text: title,
      })
    },
  })

  const defaultImage =
    md.renderer.rules.image ||
    ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

  md.renderer.rules.image = (tokens, idx, options, env, self) => {
    tokens[idx].attrSet('class', 'md-img')
    return defaultImage(tokens, idx, options, env, self)
  }

  md.renderer.rules.fence = (tokens, idx) => {
    const token = tokens[idx]
    const info = token.info ? md.utils.unescapeAll(token.info).trim() : ''
    const lang = info.split(/\s+/g)[0] || ''
    return `${renderCodeBlock(token.content, lang)}\n`
  }

  md.renderer.rules.code_block = (tokens, idx) => {
    return `${renderCodeBlock(tokens[idx].content, '')}\n`
  }

  md.renderer.rules.table_open = () => '<div class="md-table-wrap"><table class="md-table">\n'
  md.renderer.rules.table_close = () => '</table></div>\n'

  return md
}

export function sanitizeMarkdownHtml(html: string): string {
  installPurifyHooks()
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: true,
    KEEP_CONTENT: true,
  })
}

export function renderMarkdown(source: string): RenderMarkdownResult {
  const markdown = typeof source === 'string' ? source : ''
  if (!markdown.trim()) {
    return { html: '', toc: [] }
  }

  const toc: TocItem[] = []
  const md = createMarkdownIt(toc)
  const raw = md.render(markdown)
  return {
    html: sanitizeMarkdownHtml(raw),
    toc,
  }
}

export function isExternalHref(href: string): boolean {
  return /^https?:\/\//i.test(href) || href.startsWith('//')
}
