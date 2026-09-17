<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy } from 'pdfjs-dist'
// Vite emits a hashed URL; nginx must serve .mjs as application/javascript.
import pdfWorkerSrc from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = pdfWorkerSrc

export interface PdfTextHit {
  query: string
  ratio: number
  page: number
}

const props = withDefaults(
  defineProps<{
    url: string
    activeRatio?: number | null
  }>(),
  {
    activeRatio: null,
  },
)

const emit = defineEmits<{
  scroll: [ratio: number]
  ready: [hits: PdfTextHit[]]
  error: [message: string]
}>()

const { t } = useI18n()
const scroller = ref<HTMLElement | null>(null)
const pagesEl = ref<HTMLElement | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const pageCount = ref(0)
const contentHeight = ref(1)
const hits = ref<PdfTextHit[]>([])

let pdfDoc: PDFDocumentProxy | null = null
let renderToken = 0
let syncing = false
let pageHeights: number[] = []

function clamp01(n: number) {
  return Math.min(1, Math.max(0, n))
}

function ratioOf(el: HTMLElement): number {
  const max = el.scrollHeight - el.clientHeight
  if (max <= 1) return 0
  return clamp01(el.scrollTop / max)
}

function setRatio(ratio: number) {
  const el = scroller.value
  if (!el) return
  const max = el.scrollHeight - el.clientHeight
  syncing = true
  el.scrollTop = max <= 1 ? 0 : max * clamp01(ratio)
  updateHighlight(ratio)
  window.setTimeout(() => {
    syncing = false
  }, 40)
}

function updateHighlight(ratio: number | null | undefined) {
  // Highlights removed
}

function onScroll() {
  if (!scroller.value || syncing) return
  const ratio = ratioOf(scroller.value)
  updateHighlight(ratio)
  emit('scroll', ratio)
}

function clearPages() {
  if (pagesEl.value) pagesEl.value.innerHTML = ''
  pageHeights = []
  contentHeight.value = 1
  pageCount.value = 0
}

async function renderPage(pageNum: number, scale: number) {
  if (!pdfDoc || !pagesEl.value) return
  const page = await pdfDoc.getPage(pageNum)
  const viewport = page.getViewport({ scale })
  const wrap = document.createElement('div')
  wrap.className = 'pdf-page'
  wrap.dataset.page = String(pageNum)

  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')
  if (!context) return
  const outputScale = window.devicePixelRatio || 1
  canvas.width = Math.floor(viewport.width * outputScale)
  canvas.height = Math.floor(viewport.height * outputScale)
  canvas.style.width = `${viewport.width}px`
  canvas.style.height = `${viewport.height}px`
  canvas.className = 'pdf-page__canvas'
  context.setTransform(outputScale, 0, 0, outputScale, 0, 0)
  wrap.appendChild(canvas)
  pagesEl.value.appendChild(wrap)

  await page.render({ canvasContext: context, viewport }).promise

  const gap = 12
  pageHeights[pageNum - 1] = viewport.height + gap
  const yBase = pageHeights.slice(0, pageNum - 1).reduce((a, b) => a + b, 0)
  contentHeight.value = Math.max(1, pageHeights.reduce((a, b) => a + b, 0))

  const text = await page.getTextContent()
  for (const item of text.items) {
    if (!('str' in item) || !item.str?.trim()) continue
    const ty = item.transform?.[5] ?? 0
    const localY = viewport.height - ty * scale
    const docY = yBase + Math.max(0, Math.min(viewport.height, localY))
    hits.value.push({
      query: String(item.str),
      ratio: clamp01(docY / contentHeight.value),
      page: pageNum,
    })
  }
}

async function load(url: string) {
  const token = ++renderToken
  loading.value = true
  error.value = null
  hits.value = []
  clearPages()
  try {
    await pdfDoc?.destroy()
    pdfDoc = null
    pdfDoc = await getDocument({ url, withCredentials: false }).promise
    if (token !== renderToken) return
    pageCount.value = pdfDoc.numPages
    const width = scroller.value?.clientWidth || 640
    const first = await pdfDoc.getPage(1)
    const base = first.getViewport({ scale: 1 })
    const scale = Math.max(0.65, Math.min(1.4, (width - 28) / base.width))

    for (let i = 1; i <= pdfDoc.numPages; i += 1) {
      if (token !== renderToken) return
      await renderPage(i, scale)
    }

    const finalH = Math.max(1, pageHeights.reduce((a, b) => a + b, 0))
    contentHeight.value = finalH
    // Normalize hit ratios against final height
    hits.value = hits.value.map((h) => ({ ...h, ratio: clamp01(h.ratio) }))
    await nextTick()
    updateHighlight(props.activeRatio)
    emit('ready', hits.value.slice())
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('demo.loadError')
    emit('error', error.value)
  } finally {
    if (token === renderToken) loading.value = false
  }
}

function findRatioForQuery(query: string): number | null {
  const needle = query.trim().toLowerCase()
  if (!needle || needle.length < 4) return null
  const direct = hits.value.find((item) => item.query.toLowerCase().includes(needle))
  if (direct) return direct.ratio
  const parts = needle.split(/\s+/).filter((w) => w.length >= 5)
  for (const part of parts) {
    const soft = hits.value.find((item) => item.query.toLowerCase().includes(part))
    if (soft) return soft.ratio
  }
  return null
}

watch(
  () => props.url,
  (url) => {
    if (url) void load(url)
  },
  { immediate: true },
)

watch(
  () => props.activeRatio,
  (ratio) => updateHighlight(ratio),
)

onBeforeUnmount(() => {
  renderToken += 1
  void pdfDoc?.destroy()
  pdfDoc = null
})

defineExpose({
  setRatio,
  getRatio: () => (scroller.value ? ratioOf(scroller.value) : 0),
  findRatioForQuery,
  scroller,
})
</script>

<template>
  <div class="demo-pdf-viewer" data-testid="demo-pdf-viewer">
    <div v-if="loading" class="pdf-state">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="pdf-state pdf-state--error">{{ error }}</div>
    <div
      ref="scroller"
      class="pdf-scroller"
      data-testid="demo-pdf-pane"
      @scroll.passive="onScroll"
    >
      <div class="pdf-track">
        <div ref="pagesEl" class="pdf-pages" />
      </div>
    </div>
    <p v-if="pageCount" class="pdf-pages-label">{{ pageCount }} pág.</p>
  </div>
</template>

<style scoped>
.demo-pdf-viewer {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: #e8eef1;
}

.pdf-scroller {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0.75rem;
}

.pdf-track {
  position: relative;
}

.pdf-pages {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: center;
}

.pdf-pages :deep(.pdf-page) {
  position: relative;
  box-shadow: 0 8px 24px rgb(11 31 42 / 0.12);
  background: #fff;
  border-radius: 2px;
  overflow: hidden;
}

.pdf-pages :deep(.pdf-page__canvas) {
  display: block;
  max-width: 100%;
  height: auto;
}

.pdf-state {
  padding: 2rem 1rem;
  text-align: center;
  color: var(--bv-ink-muted, #6b8290);
}

.pdf-state--error {
  color: var(--bv-danger, #c0362c);
}

.pdf-pages-label {
  margin: 0;
  padding: 0.35rem 0.75rem;
  font-size: 0.75rem;
  color: var(--bv-ink-muted, #6b8290);
  border-top: 1px solid var(--bv-border, #cfdce2);
  background: #fff;
}
</style>
