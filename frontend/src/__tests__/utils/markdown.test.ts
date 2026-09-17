import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import MarkdownViewer from '@/components/markdown/MarkdownViewer.vue'
import { renderMarkdown, sanitizeMarkdownHtml } from '@/utils/markdown'
import { slugifyHeading, uniqueSlug } from '@/utils/markdown/slugify'
import summaryEsHeadings from '@/__tests__/fixtures/summary-es-headings.md?raw'
import summaryEsTablesCode from '@/__tests__/fixtures/summary-es-tables-code.md?raw'
import summaryEsLong from '@/__tests__/fixtures/summary-es-long-imperfect.md?raw'
import summaryEnShort from '@/__tests__/fixtures/summary-en-short.md?raw'
import pdfExportSample from '@/__tests__/fixtures/pdf-export-sample.md?raw'

function asDom(html: string) {
  const root = document.createElement('div')
  root.innerHTML = html
  return root
}

describe('slugifyHeading', () => {
  it('keeps international characters and avoids duplicates', () => {
    expect(slugifyHeading('Economía: Fundamentos')).toContain('econom')
    expect(slugifyHeading('Árbol 🌳')).toBeTruthy()
    const used = new Set<string>()
    expect(uniqueSlug('intro', used)).toBe('intro')
    expect(uniqueSlug('intro', used)).toBe('intro-1')
  })
})

describe('renderMarkdown', () => {
  it('renders headings paragraphs lists tables code blockquotes links images and task lists', () => {
    const md = `
# Título H1
## Capítulo H2
### Sección H3
#### Sub H4
##### Deep H5
###### Tiny H6

Paragraph with **bold**, *italic*, ~~strike~~ and a [link](https://example.com).

- Item
  - Nested
1. Primero
2. Segundo

- [x] Completado
- [ ] Pendiente

> Cita importante

\`inline\`

\`\`\`python
async def example():
    return 1
\`\`\`

| Concepto | Descripción |
|----------|-------------|
| Async    | Alta        |

![alt text](https://example.com/a.png)

https://brevio.example/autolink

---`

    const { html, toc } = renderMarkdown(md)
    const root = asDom(html)

    expect(root.querySelector('h1')?.textContent).toContain('Título H1')
    expect(root.querySelector('h2')).toBeTruthy()
    expect(root.querySelector('h3')).toBeTruthy()
    expect(root.querySelector('h6')).toBeTruthy()
    expect(root.querySelector('strong')?.textContent).toBe('bold')
    expect(root.querySelector('em')?.textContent).toBe('italic')
    expect(root.querySelector('s, del')).toBeTruthy()
    expect(root.querySelector('a[href="https://example.com"]')).toBeTruthy()
    expect(root.querySelector('a[rel="noopener noreferrer"]')).toBeTruthy()
    expect(root.querySelectorAll('ul li').length).toBeGreaterThan(1)
    expect(root.querySelector('ol')).toBeTruthy()
    expect(root.querySelector('blockquote')?.textContent).toContain('Cita')
    expect(root.querySelector('code')?.textContent).toContain('inline')
    expect(root.querySelector('.md-code')).toBeTruthy()
    expect(root.querySelector('.md-code__copy')).toBeTruthy()
    expect(root.querySelector('.md-table')).toBeTruthy()
    expect(root.querySelector('.md-table-wrap')).toBeTruthy()
    expect(root.querySelector('img.md-img')?.getAttribute('alt')).toBe('alt text')
    expect(root.querySelector('hr')).toBeTruthy()
    expect(root.querySelector('input[type="checkbox"]')).toBeTruthy()
    expect(toc.length).toBeGreaterThanOrEqual(6)
    expect(toc[0]?.id).toBeTruthy()
  })

  it('handles empty invalid unicode spanish english and long content', () => {
    expect(renderMarkdown('').html).toBe('')
    expect(renderMarkdown('   ').html).toBe('')
    expect(renderMarkdown('not really markdown but **ok**').html).toContain('<strong>')
    expect(renderMarkdown('emoji 🙂 and 日本語 and Español').html).toContain('🙂')

    const es = renderMarkdown(summaryEsHeadings)
    expect(es.html).toContain('Economía')
    expect(es.toc.length).toBeGreaterThan(3)

    const tables = renderMarkdown(summaryEsTablesCode)
    expect(tables.html).toContain('md-table')
    expect(tables.html).toContain('md-code')

    const long = renderMarkdown(summaryEsLong)
    expect(long.html.length).toBeGreaterThan(1000)

    const en = renderMarkdown(summaryEnShort)
    expect(en.html.toLowerCase()).toContain('javascript')
  })

  it('renders the PDF export sample with the same semantic HTML the backend exports', () => {
    const { html } = renderMarkdown(pdfExportSample)
    const root = asDom(html)
    expect(root.querySelector('h1')?.textContent).toContain('Título principal')
    expect(root.querySelector('h2')?.textContent).toContain('Sección')
    expect(root.querySelector('h3')?.textContent).toContain('Subsección')
    expect(root.querySelector('strong')?.textContent).toBe('negrita')
    expect(root.querySelector('em')?.textContent).toBe('cursiva')
    expect(root.querySelector('a[href="https://example.com"]')).toBeTruthy()
    expect(root.querySelector('ul')).toBeTruthy()
    expect(root.querySelector('ul ul')).toBeTruthy()
    expect(root.querySelector('ol')).toBeTruthy()
    expect(root.querySelector('blockquote')?.textContent).toContain('Esto es una cita')
    expect(root.querySelector('hr')).toBeTruthy()
    expect(root.querySelector('.md-code')).toBeTruthy()
    expect(root.querySelector('.md-code pre code')?.textContent).toContain('async def main')
    expect(root.querySelector('.md-code pre code')?.textContent).toMatch(/\n\s+print/)
    expect(root.querySelector('.md-table')).toBeTruthy()
    expect(root.querySelector('th')?.textContent).toContain('Campo')
    expect(html).toContain('8192')
    expect(html).toContain('ñ')
  })

  it('sanitizes xss payloads', () => {
    const payloads = [
      `<script>alert('xss')</script>`,
      `<img src=x onerror=alert(1)>`,
      `[javascript](javascript:alert(1))`,
      `<a href="javascript:alert(1)">x</a>`,
      `<img src="x" onerror="alert(1)">`,
    ]

    for (const payload of payloads) {
      const { html } = renderMarkdown(payload)
      const root = asDom(html)
      expect(root.querySelector('script')).toBeNull()
      root.querySelectorAll('*').forEach((el) => {
        for (const attr of Array.from(el.attributes)) {
          expect(attr.name.toLowerCase()).not.toMatch(/^on/)
          expect(attr.value.toLowerCase()).not.toContain('javascript:')
        }
      })
      root.querySelectorAll('a').forEach((a) => {
        expect((a.getAttribute('href') || '').toLowerCase()).not.toContain('javascript:')
      })
    }

    const dirty = sanitizeMarkdownHtml(
      `<img src=x onerror=alert(1)><script>alert(1)</script><a href="javascript:alert(1)">x</a>`,
    )
    const cleaned = asDom(dirty)
    expect(cleaned.querySelector('script')).toBeNull()
    cleaned.querySelectorAll('img').forEach((img) => {
      expect(img.getAttribute('onerror')).toBeNull()
    })
    cleaned.querySelectorAll('a').forEach((a) => {
      expect((a.getAttribute('href') || '').toLowerCase()).not.toContain('javascript:')
    })
  })
})

describe('MarkdownViewer', () => {
  it('renders markdown body and toc', async () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        source: '# Intro\n\n## Details\n\nHello world\n\n```js\nconsole.log(1)\n```\n',
      },
      attachTo: document.body,
    })

    expect(wrapper.find('[data-testid="markdown-viewer"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="markdown-body"]').html()).toContain('Hello world')
    expect(wrapper.find('[data-testid="markdown-toc"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="markdown-toc"] .md-toc__nav.is-open').exists()).toBe(true)
    expect(wrapper.find('[data-testid="markdown-toc"]').text()).toContain('Intro')
    expect(wrapper.find('[data-testid="markdown-toc"]').text()).toContain('Details')
    expect(wrapper.text()).toContain('Copy')
    wrapper.unmount()
  })

  it('starts with toc closed when tocDefaultOpen is false', async () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        source: '# Intro\n\n## Details\n\nHello\n',
        tocDefaultOpen: false,
      },
    })
    expect(wrapper.find('.md-layout--toc-closed').exists()).toBe(true)
    expect(wrapper.find('[data-testid="markdown-toc"] .md-toc__nav.is-open').exists()).toBe(false)
    await wrapper.find('[data-testid="markdown-toc-toggle"]').trigger('click')
    expect(wrapper.find('.md-layout--toc-open').exists()).toBe(true)
    expect(wrapper.find('[data-testid="markdown-toc"] .md-toc__nav.is-open').exists()).toBe(true)
    wrapper.unmount()
  })

  it('shows empty and error states', () => {
    const empty = mount(MarkdownViewer, { props: { source: '' } })
    expect(empty.find('[data-testid="markdown-empty"]').exists()).toBe(true)
    empty.unmount()

    const errored = mount(MarkdownViewer, {
      props: { source: '# x', error: 'boom' },
    })
    expect(errored.find('[data-testid="markdown-error"]').text()).toContain('boom')
    errored.unmount()
  })

  it('updates reading progress on scroll and uses a track fill', async () => {
    const long = Array.from({ length: 80 }, (_, i) => `## Section ${i}\n\nParagraph ${i}.\n`).join('\n')
    const wrapper = mount(MarkdownViewer, {
      props: { source: long },
      attachTo: document.body,
    })
    await nextTick()
    const body = wrapper.find('[data-testid="markdown-body"]').element as HTMLElement
    Object.defineProperty(body, 'scrollHeight', { configurable: true, get: () => 2000 })
    Object.defineProperty(body, 'clientHeight', { configurable: true, get: () => 400 })
    Object.defineProperty(body, 'scrollTop', { configurable: true, writable: true, value: 0 })
    body.dispatchEvent(new Event('scroll'))
    await nextTick()
    expect(wrapper.find('.md-progress__label').text()).toBe('0%')
    expect((wrapper.find('.md-progress__bar').element as HTMLElement).style.width).toBe('0%')

    body.scrollTop = 800
    body.dispatchEvent(new Event('scroll'))
    await nextTick()
    expect(wrapper.find('.md-progress__label').text()).toBe('50%')
    expect((wrapper.find('.md-progress__bar').element as HTMLElement).style.width).toBe('50%')
    wrapper.unmount()
  })
})
