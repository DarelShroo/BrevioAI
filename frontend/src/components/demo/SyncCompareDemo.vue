<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import Select from 'primevue/select'
import { ArrowDown, MousePointerClick, Sparkles } from '@lucide/vue'
import MarkdownViewer from '@/components/markdown/MarkdownViewer.vue'
import DemoPdfViewer, { type PdfTextHit } from '@/components/demo/DemoPdfViewer.vue'
import {
  examplePdfUrl,
  fetchExampleSummary,
  getExample,
  listExamples,
  type ExampleEntry,
} from '@/services/examples.service'
import { parseApiError } from '@/utils/errors'
import { categoryLabel, styleLabel, summaryLevelLabel } from '@/utils/labels'

interface SyncAnchor {
  id: string
  label: string
  summaryRatio: number
  pdfRatio: number
}

const props = withDefaults(
  defineProps<{
    slug?: string | null
    compact?: boolean
    showRegisterCta?: boolean
    preferCategory?: string | null
    preferStyle?: string | null
    preferModel?: string | null
  }>(),
  {
    slug: null,
    compact: false,
    showRegisterCta: true,
    preferCategory: null,
    preferStyle: null,
    preferModel: null,
  },
)

const emit = defineEmits<{
  'update:slug': [value: string]
}>()

const { t, te } = useI18n()
const catalog = ref<ExampleEntry[]>([])
const defaultSlug = ref('summary_d89204')
const selectedSlug = ref('')
const entry = ref<ExampleEntry | null>(null)
const summary = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const showScrollHint = ref(true)
const activeRatio = ref(0.12)
const activeAnchorId = ref<string | null>(null)
const anchors = ref<SyncAnchor[]>([])
const pdfViewer = ref<InstanceType<typeof DemoPdfViewer> | null>(null)
const summaryPane = ref<HTMLElement | null>(null)

let boundSummaryScroll: HTMLElement | null = null
let syncing = false
let pdfHits: PdfTextHit[] = []

const options = computed(() =>
  catalog.value.map((item) => ({
    label: exampleOptionLabel(item),
    value: item.slug,
  })),
)

const pdfUrl = computed(() => (selectedSlug.value ? examplePdfUrl(selectedSlug.value) : ''))
const typeLabel = computed(() => (entry.value ? exampleTypeLabel(entry.value) : ''))
const documentLabel = computed(() => {
  const name = entry.value?.document_name || 'PDF'
  return name.replace(/__benchmark_p\d+-\d+/i, '').replace(/_/g, ' ').replace(/\.pdf$/i, '')
})
const primaryCtaTo = computed(() =>
  props.showRegisterCta ? { name: 'register' as const } : { name: 'summary' as const },
)

function styleLabelFor(item: ExampleEntry): string {
  const cat = (item.category_key || item.category || '').trim()
  const style = (item.style_key || item.style || '').trim()
  return styleLabel(cat, style, t, te)
}

function exampleTypeLabel(item: ExampleEntry): string {
  const cat = categoryLabel(item.category_key || item.category, t, te)
  const style = styleLabelFor(item)
  const level = summaryLevelLabel(item.summary_level, t, te)
  return [cat, style, level].filter(Boolean).join(' · ')
}

function exampleOptionLabel(item: ExampleEntry): string {
  const type = exampleTypeLabel(item)
  return type ? `${item.title} · ${type}` : item.title
}

function summaryScrollEl(): HTMLElement | null {
  return summaryPane.value?.querySelector('.md-body') as HTMLElement | null
}

function clamp01(n: number) {
  return Math.min(1, Math.max(0, n))
}

function ratioOf(el: HTMLElement): number {
  const max = el.scrollHeight - el.clientHeight
  if (max <= 1) return 0
  return clamp01(el.scrollTop / max)
}

function setElRatio(el: HTMLElement, ratio: number) {
  const max = el.scrollHeight - el.clientHeight
  if (max <= 1) {
    el.scrollTop = 0
    return
  }
  el.scrollTop = max * clamp01(ratio)
}

function extractSectionLabels(md: string): string[] {
  const labels: string[] = []
  for (const line of md.split('\n')) {
    const heading = line.match(/^#{1,3}\s+(.+)$/)
    if (heading?.[1]) {
      labels.push(heading[1].replace(/[*_`]/g, '').trim())
      continue
    }
    const bold = line.match(/^\*\*(.+?)\*\*/)
    if (bold?.[1]) {
      labels.push(bold[1].replace(/[*_`]/g, '').trim())
    }
  }
  const seen = new Set<string>()
  return labels.filter((label) => {
    const key = label.toLowerCase()
    if (key.length < 4 || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function buildAnchors() {
  const body = summaryScrollEl()
  const labels = extractSectionLabels(summary.value)
  const built: SyncAnchor[] = []
  const maxScroll = body ? Math.max(1, body.scrollHeight - body.clientHeight) : 1

  labels.forEach((label, index) => {
    const spread = labels.length <= 1 ? 0 : index / (labels.length - 1)
    let summaryRatio = spread
    if (body) {
      const nodes = body.querySelectorAll<HTMLElement>('h1, h2, h3, h4, strong, li, p')
      for (const node of nodes) {
        if ((node.textContent || '').toLowerCase().includes(label.toLowerCase())) {
          summaryRatio = clamp01(node.offsetTop / maxScroll)
          break
        }
      }
    }

    let pdfRatio = pdfViewer.value?.findRatioForQuery(label) ?? spread
    const manifestHit = (entry.value?.highlights || []).find(
      (h) =>
        h.summary_match &&
        label.toLowerCase().includes(String(h.summary_match).toLowerCase()),
    )
    if (manifestHit?.pdf_ratio != null) pdfRatio = Number(manifestHit.pdf_ratio)

    built.push({
      id: `a-${index}`,
      label,
      summaryRatio,
      pdfRatio: clamp01(pdfRatio),
    })
  })

  built.unshift({ id: 'a-start', label: '', summaryRatio: 0, pdfRatio: 0 })
  built.push({ id: 'a-end', label: '', summaryRatio: 1, pdfRatio: 1 })

  let prev = -0.001
  for (const anchor of built) {
    if (anchor.summaryRatio < prev) anchor.summaryRatio = prev
    prev = anchor.summaryRatio
  }
  built[built.length - 1].summaryRatio = 1
  built[built.length - 1].pdfRatio = 1

  anchors.value = built
}

function highlightForRatio(ratio: number, key: 'summaryRatio' | 'pdfRatio') {
  if (!anchors.value.length) return
  let best = anchors.value[0]
  let bestDist = Math.abs(best[key] - ratio)
  for (const anchor of anchors.value) {
    if (!anchor.label) continue
    const dist = Math.abs(anchor[key] - ratio)
    if (dist < bestDist) {
      best = anchor
      bestDist = dist
    }
  }
  if (best.label) applyActiveHighlight(best.id)
  activeRatio.value = ratio
}

function syncFromSummary() {
  const body = summaryScrollEl()
  if (!body || syncing) return
  const ratio = ratioOf(body)
  syncing = true
  showScrollHint.value = false
  highlightForRatio(ratio, 'summaryRatio')
  pdfViewer.value?.setRatio(ratio)
  window.setTimeout(() => {
    syncing = false
  }, 32)
}

function syncFromPdf(ratio: number) {
  if (syncing) return
  const body = summaryScrollEl()
  if (!body) return
  const r = clamp01(ratio)
  syncing = true
  showScrollHint.value = false
  highlightForRatio(r, 'pdfRatio')
  setElRatio(body, r)
  window.setTimeout(() => {
    syncing = false
  }, 32)
}

function onPdfReady(readyHits: PdfTextHit[]) {
  pdfHits = readyHits
  void pdfHits
  void nextTick(async () => {
    bindSummaryScroll()
    buildAnchors()
    await new Promise((r) => window.setTimeout(r, 100))
    bindSummaryScroll()
    buildAnchors()
    syncing = true
    pdfViewer.value?.setRatio(0)
    const body = summaryScrollEl()
    if (body) setElRatio(body, 0)
    highlightForRatio(0, 'summaryRatio')
    window.setTimeout(() => {
      syncing = false
    }, 50)
  })
}

function applyActiveHighlight(id: string | null) {
  activeAnchorId.value = id
  const root = summaryScrollEl()
  if (!root) return
  root.querySelectorAll('.demo-hl').forEach((el) => el.classList.remove('demo-hl'))
  if (!id) return
  const anchor = anchors.value.find((a) => a.id === id)
  if (!anchor?.label) return
  const nodes = root.querySelectorAll<HTMLElement>('h1, h2, h3, h4, strong, li, p')
  for (const node of nodes) {
    if ((node.textContent || '').toLowerCase().includes(anchor.label.toLowerCase())) {
      node.classList.add('demo-hl')
      break
    }
  }
}

function bindSummaryScroll() {
  const el = summaryScrollEl()
  if (boundSummaryScroll === el) return
  if (boundSummaryScroll) {
    boundSummaryScroll.removeEventListener('scroll', syncFromSummary)
  }
  boundSummaryScroll = el
  el?.addEventListener('scroll', syncFromSummary, { passive: true })
}

async function loadCatalog() {
  const data = await listExamples()
  catalog.value = data.entries || []
  defaultSlug.value = data.default_slug || catalog.value[0]?.slug || 'summary_d89204'
}

function normalizeKey(value: string | null | undefined): string {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
}

function pickSlugForPrefs(): string {
  const cat = normalizeKey(props.preferCategory)
  const style = normalizeKey(props.preferStyle)
  const model = normalizeKey(props.preferModel)
  const entries = catalog.value
  if (!entries.length) return defaultSlug.value

  const score = (item: ExampleEntry) => {
    let s = 0
    const itemCat = normalizeKey(item.category_key || item.category)
    const itemStyle = normalizeKey(item.style_key || item.style)
    const itemModel = normalizeKey(item.model)
    if (cat && (itemCat === cat || itemCat.includes(cat) || cat.includes(itemCat))) s += 4
    if (style && (itemStyle === style || itemStyle.includes(style) || style.includes(itemStyle))) s += 2
    if (model && itemModel && (itemModel === model || itemModel.includes(model))) s += 1
    if (item.default) s += 0.5
    return s
  }

  const ranked = [...entries].sort((a, b) => score(b) - score(a))
  if (score(ranked[0]) > 0) return ranked[0].slug
  return defaultSlug.value
}

async function loadEntry(slug: string) {
  if (!slug) return
  loading.value = true
  error.value = null
  try {
    entry.value = await getExample(slug)
    summary.value = await fetchExampleSummary(slug)
    await nextTick()
    bindSummaryScroll()
    buildAnchors()
  } catch (err) {
    entry.value = null
    summary.value = ''
    error.value = parseApiError(err) || t('demo.loadError')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.slug,
  (value) => {
    const next = (value || defaultSlug.value || '').trim()
    if (next && next !== selectedSlug.value) selectedSlug.value = next
  },
)

watch(selectedSlug, (value) => {
  if (!value) return
  emit('update:slug', value)
  void loadEntry(value)
})

watch(summary, async () => {
  await nextTick()
  bindSummaryScroll()
  buildAnchors()
})

onMounted(async () => {
  try {
    await loadCatalog()
    const preferred = pickSlugForPrefs()
    selectedSlug.value = (props.slug || preferred || defaultSlug.value).trim()
  } catch (err) {
    error.value = parseApiError(err) || t('demo.loadError')
  }
})

watch(
  () => [props.preferCategory, props.preferStyle, props.preferModel] as const,
  () => {
    if (props.slug) return
    if (!catalog.value.length) return
    const next = pickSlugForPrefs()
    if (next && next !== selectedSlug.value) selectedSlug.value = next
  },
)

onBeforeUnmount(() => {
  if (boundSummaryScroll) {
    boundSummaryScroll.removeEventListener('scroll', syncFromSummary)
    boundSummaryScroll = null
  }
})
</script>

<template>
  <section class="demo" :class="{ 'demo--compact': compact }" data-testid="sync-compare-demo">
    
    <!-- Hero Rediseñado: Fondo claro (#ffffff), textos en marino (#061a24), CTA principal menta (#2dd4bf) -->
    <header class="demo-banner demo-banner--clean">
      <p class="demo-kicker">
        <Sparkles :size="15" :stroke-width="2.25" aria-hidden="true" />
        {{ t('demo.badge') }}
      </p>
      <h2 class="demo-title">{{ t('demo.bannerTitle') }}</h2>
      <p class="demo-subtitle">{{ t('demo.bannerSubtitle') }}</p>
      <div class="demo-banner__actions">
        <RouterLink class="cta-primary" :to="primaryCtaTo">{{ t('demo.tryFree') }}</RouterLink>
        <RouterLink v-if="showRegisterCta" class="cta-secondary" :to="{ name: 'register' }">
          {{ t('demo.register') }}
        </RouterLink>
      </div>
    </header>

    <!-- Toolbar simplificada unificada con el Selector -->
    <div class="demo-toolbar">
      <div class="demo-toolbar__main">
         <span class="demo-toolbar__title">{{ t('demo.explorerTitle') }}</span>
      </div>
      <Select
        v-if="options.length"
        v-model="selectedSlug"
        :options="options"
        option-label="label"
        option-value="value"
        class="demo-select"
        :aria-label="t('demo.pickExample')"
        data-testid="demo-example-select"
      />
    </div>

    <!-- Visor de documentos principal -->
    <div class="demo-stage">
      <div v-if="error" class="demo-error" role="alert">{{ error }}</div>

      <div v-else class="demo-split">
        <!-- PDF Columna -->
        <article class="demo-pane demo-pane--pdf">
          <header class="demo-pane__head">
            <h4>{{ t('demo.original') }}</h4>
            <span class="muted" :title="entry?.document_name || t('fileKind.pdf')">{{ documentLabel }}</span>
          </header>
          <div class="demo-pane__body demo-pane__body--pdf">
            <div class="demo-pdf-wrapper">
              <DemoPdfViewer
                v-if="pdfUrl"
                ref="pdfViewer"
                :url="pdfUrl"
                :active-ratio="activeRatio"
                @scroll="syncFromPdf"
                @ready="onPdfReady"
              />
              <div v-else class="demo-placeholder">{{ t('common.loading') }}</div>
            </div>
          </div>
          <footer class="demo-pane__foot">
            <a
              v-if="pdfUrl"
              class="demo-link-btn demo-link-btn--text"
              :href="pdfUrl"
              target="_blank"
              rel="noopener"
            >
              <ArrowDown :size="14" :stroke-width="2.5" /> {{ t('demo.downloadPdf') }}
            </a>
          </footer>
        </article>

        <!-- Summary Columna -->
        <article ref="summaryPane" class="demo-pane demo-pane--summary">
          <header class="demo-pane__head">
            <h4>{{ t('demo.faithfulSummary') }}</h4>
            <span class="demo-progress-pill">{{ Math.round(activeRatio * 100) }}%</span>
          </header>
          
          <!-- Chips minimalistas para la metadata -->
          <div v-if="entry" class="demo-meta demo-meta--clean">
            <span class="demo-meta-chip">{{ categoryLabel(entry.category_key || entry.category, t, te) }}</span>
            <span class="demo-meta-chip">{{ styleLabelFor(entry) }}</span>
            <span v-if="entry.summary_level" class="demo-meta-chip">
              {{ summaryLevelLabel(entry.summary_level, t, te) }}
            </span>
            <span class="demo-meta-chip">{{ entry.model }}</span>
          </div>

          <div class="demo-pane__body demo-summary">
            <!-- Quitamos el connector verde para que quede más limpio -->
            <MarkdownViewer
              :source="summary"
              :loading="loading"
              :error="null"
              :toc-default-open="false"
            />
          </div>
          <footer class="demo-pane__foot demo-pane__foot--end">
            <!-- Solo un botón secundario discreto abajo para no repetir el peso del CTA -->
            <RouterLink class="demo-link-btn" :to="primaryCtaTo">
              {{ t('demo.tryOwn') }}
            </RouterLink>
          </footer>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.demo {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  background-color: #f8fafc;
  padding: 1.5rem;
  border-radius: 12px;
}

/* 1. ELIMINAR EL BANNER OSCURO Y USAR DISEÑO CLARO/MARINO */
.demo-banner--clean {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0;
  padding: 2rem 2.5rem;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.demo-kicker {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: #2dd4bf; /* Verde menta del logo */
}

.demo-title {
  margin: 0;
  max-width: 52rem;
  font-size: clamp(1.4rem, 2.5vw, 2rem);
  line-height: 1.25;
  font-weight: 800;
  color: #061a24; /* Azul marino profundo */
}

.demo-subtitle {
  margin: 0.75rem 0 0;
  max-width: 44rem;
  color: #475569;
  font-size: 1.05rem;
  line-height: 1.5;
  font-weight: 400;
}

.demo-banner__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
  margin-top: 1.5rem;
}

/* 3. JERARQUÍA DE BOTONES Y CTAS */
.cta-primary,
.cta-secondary,
.demo-link-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.6rem 1.25rem;
  border-radius: 999px;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 700;
  transition: all 0.2s;
}

/* CTA Primario: Verde menta con texto oscuro */
.cta-primary {
  background: #2dd4bf;
  color: #061a24;
  box-shadow: 0 2px 4px rgba(45, 212, 191, 0.2);
}

.cta-primary:hover {
  background: #5eead4;
}

/* CTA Secundario: Outline limpio */
.cta-secondary {
  border: 1px solid #cbd5e1;
  color: #061a24;
  background: #ffffff;
}

.cta-secondary:hover {
  background: #f1f5f9;
}

/* Toolbar Integrado */
.demo-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-bottom: none;
  border-radius: 12px 12px 0 0;
  padding: 0.85rem 1.25rem;
  margin-bottom: -0.35rem; /* pull up to stage */
  position: relative;
  z-index: 2;
}

.demo-toolbar__main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.demo-toolbar__main::before {
  content: '';
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #2dd4bf;
  box-shadow: 0 0 8px rgba(45, 212, 191, 0.5);
}

.demo-toolbar__title {
  font-size: 0.9rem;
  font-weight: 700;
  color: #061a24;
}

.demo-select {
  min-width: 18rem;
  max-width: 24rem;
  border-radius: 8px;
}

/* 4. VISOR DE DOCUMENTOS Y RESUMEN (WORKSPACE) */
.demo-stage {
  position: relative;
  border: 1px solid #e2e8f0;
  border-radius: 0 0 12px 12px;
  background: #ffffff;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: min(75vh, 46rem);
}

.demo--compact .demo-stage {
  height: min(58vh, 34rem);
}

.demo-split {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.18fr);
  flex: 1;
  min-height: 0;
}

.demo-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  border-inline-end: 1px solid #e2e8f0;
  background: #f8fafc;
}

.demo-pane:last-child {
  border-inline-end: 0;
}

.demo-pane__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
  flex-shrink: 0;
}

.demo-pane__head h4 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #061a24;
}

/* Badge del archivo original */
.muted {
  color: #475569;
  font-size: 0.75rem;
  font-weight: 600;
  background: #f1f5f9;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

/* Píldora de progreso en la derecha */
.demo-progress-pill {
  font-size: 0.75rem;
  font-weight: 800;
  color: #061a24;
  background: #f0fdfa; /* teal-50 */
  border: 1px solid #2dd4bf;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
}

/* Metadatos (Chips) */
.demo-meta--clean {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 0.6rem 1.25rem;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
  flex-shrink: 0;
}

.demo-meta-chip {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: #64748b;
  background: #ffffff;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}

.demo-pane__body {
  position: relative;
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
  background: #ffffff;
}

/* Fondo gris sutil para el PDF y contenedor blanco interno */
.demo-pane__body--pdf {
  background: #f1f5f9;
  padding: 1rem;
}

.demo-pdf-wrapper {
  width: 100%;
  height: 100%;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.demo-summary {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* Markdown Viewer Configuration */
.demo-summary :deep(.markdown-viewer) {
  flex: 1;
  min-height: 0;
  height: 100%;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

/* Aumentar padding interno y espaciado para evitar sensación de compresión */
.demo-summary :deep(.md-body) {
  padding: 2.5rem 3rem !important;
  font-size: 1.05rem;
  line-height: 1.75;
  color: var(--md-ink, #0b1f2a);
  max-width: 70ch;
  margin: 0 auto;
}

.demo-summary :deep(.md-body h1),
.demo-summary :deep(.md-body h2),
.demo-summary :deep(.md-body h3) {
  color: var(--md-ink, #061a24);
}

.demo-summary :deep(.md-body p),
.demo-summary :deep(.md-body li) {
  color: var(--md-ink-soft, #355064);
}

/* Rediseño del resaltado de sincronización: Menta muy sutil, sin fondo pesado */
.demo-summary :deep(.demo-hl),
.demo-summary :deep(.md-body .demo-hl) {
  background: rgba(45, 212, 191, 0.1) !important;
  box-shadow: inset 3px 0 0 0 #2dd4bf;
  border-radius: 0 6px 6px 0;
  transition: all 0.2s;
  padding-left: 0.75rem;
}

.demo-pane__foot {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
}

.demo-pane__foot--end {
  justify-content: flex-end;
}

/* Enlace/Botón descargar PDF */
.demo-link-btn--text {
  border: none;
  background: transparent;
  color: #0f766e;
  padding: 0;
  font-size: 0.8rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.demo-link-btn--text:hover {
  color: #042f2e;
}

/* Botón secundario en el footer derecho */
.demo-link-btn {
  border: 1px solid #99f6e4;
  color: #061a24;
  background: #f0fdfa;
  padding: 0.45rem 1rem;
  font-size: 0.8rem;
}
.demo-link-btn:hover {
  background: #ccfbf1;
}

.demo-error,
.demo-placeholder {
  padding: 2rem 1rem;
  text-align: center;
  color: #64748b;
}

.demo-error {
  color: #ef4444;
}

[data-theme='dark'] .demo-stage,
.p-dark .demo-stage {
  border-color: #30363d;
  background: #0d1117;
}

[data-theme='dark'] .demo-pane,
.p-dark .demo-pane {
  background: #0d1117;
  border-color: #30363d;
}

[data-theme='dark'] .demo-pane__head,
.p-dark .demo-pane__head {
  background: #161b22;
  border-color: #30363d;
}

[data-theme='dark'] .demo-pane__head h4,
.p-dark .demo-pane__head h4 {
  color: #e6edf3;
}

[data-theme='dark'] .demo-pane__body,
.p-dark .demo-pane__body {
  background: #0d1117;
}

[data-theme='dark'] .demo-pane__body--pdf,
.p-dark .demo-pane__body--pdf {
  background: #161b22;
}

[data-theme='dark'] .demo-pane__foot,
.p-dark .demo-pane__foot {
  background: #161b22;
  border-color: #30363d;
}

[data-theme='dark'] .demo-meta--clean,
.p-dark .demo-meta--clean {
  background: #161b22;
  border-color: #30363d;
}

[data-theme='dark'] .demo-meta-chip,
.p-dark .demo-meta-chip {
  background: #21262d;
  color: #c9d1d9;
  border-color: #30363d;
}

@media (max-width: 960px) {
  .demo-stage {
    height: auto;
    min-height: 42rem;
  }

  .demo-split {
    grid-template-columns: 1fr;
  }

  .demo-pane {
    border-inline-end: 0;
    border-bottom: 1px solid #e2e8f0;
    height: 28rem;
  }

  .demo-pane:last-child {
    border-bottom: 0;
  }

  .demo-summary :deep(.md-body) {
    padding: 1.25rem 1rem !important;
  }
}
</style>
