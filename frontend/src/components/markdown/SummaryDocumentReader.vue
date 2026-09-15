<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import MarkdownViewer from '@/components/markdown/MarkdownViewer.vue'
import * as brevioService from '@/services/brevio.service'
import { parseApiError } from '@/utils/errors'
import { ApiError } from '@/types/api'

const props = withDefaults(
  defineProps<{
    folderEntryId: string
    resultIndex?: number
    status?: string | null
    phase?: string | null
    enabled?: boolean
  }>(),
  {
    resultIndex: 0,
    status: null,
    phase: null,
    enabled: true,
  },
)

const { t } = useI18n()
const source = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
let requestSeq = 0

const normalizedStatus = computed(() => String(props.status || '').toUpperCase())
const isProcessing = computed(() => {
  const status = normalizedStatus.value
  return !status || status === 'PROCESSING' || status === 'UNKNOWN' || status === 'QUEUED'
})
const isFailed = computed(() => normalizedStatus.value === 'FAILED')
const canFetch = computed(
  () => props.enabled && Boolean(props.folderEntryId) && normalizedStatus.value === 'COMPLETED',
)

async function load() {
  if (!canFetch.value) {
    source.value = ''
    error.value = null
    loading.value = false
    return
  }

  const seq = ++requestSeq
  loading.value = true
  error.value = null
  try {
    const text = await brevioService.fetchSummaryMarkdown(props.folderEntryId, props.resultIndex)
    if (seq !== requestSeq) return
    source.value = text
  } catch (err) {
    if (seq !== requestSeq) return
    source.value = ''
    const statusCode =
      err instanceof ApiError
        ? err.status
        : err && typeof err === 'object' && 'response' in err
          ? Number((err as { response?: { status?: number } }).response?.status)
          : NaN
    if (statusCode === 409) {
      error.value = null
      return
    }
    error.value = parseApiError(err) || t('store.summaryLoadError')
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}

watch(
  () =>
    [props.folderEntryId, props.resultIndex, props.enabled, normalizedStatus.value] as const,
  () => {
    void load()
  },
  { immediate: true },
)
</script>

<template>
  <section class="summary-reader" data-testid="summary-reader">
    <div
      v-if="isProcessing"
      class="reader-placeholder"
      data-testid="summary-processing"
      role="status"
    >
      <div class="reader-art" aria-hidden="true">
        <span class="reader-art__page" />
        <span class="reader-art__page reader-art__page--mid" />
        <span class="reader-art__page reader-art__page--front" />
        <span class="reader-art__scan" />
      </div>
      <h3>{{ t('store.summaryNotReadyTitle') }}</h3>
      <p>{{ t('store.summaryNotReadyBody') }}</p>
      <p v-if="phase" class="reader-phase">{{ phase }}</p>
    </div>

    <div
      v-else-if="isFailed"
      class="reader-placeholder reader-placeholder--failed"
      data-testid="summary-failed"
      role="alert"
    >
      <div class="reader-art reader-art--failed" aria-hidden="true">
        <span class="reader-art__page" />
        <span class="reader-art__cross" />
      </div>
      <h3>{{ t('store.summaryFailedTitle') }}</h3>
      <p>{{ t('store.summaryFailedBody') }}</p>
    </div>

    <MarkdownViewer v-else :source="source" :loading="loading" :error="error" />
  </section>
</template>

<style scoped>
.summary-reader {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
  min-height: 0;
  flex: 1;
  height: 100%;
}

.summary-reader :deep(.markdown-viewer) {
  flex: 1 1 0;
  min-height: 0;
  height: auto;
  max-height: 100%;
}

.reader-placeholder {
  flex: 1;
  min-height: 14rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  text-align: center;
  padding: 2rem 1.5rem;
  border: 1px solid var(--bv-border, #cfdce2);
  border-radius: var(--bv-radius-sm, 12px);
  background:
    radial-gradient(circle at 20% 20%, rgba(31, 184, 168, 0.12), transparent 42%),
    radial-gradient(circle at 80% 10%, rgba(245, 158, 11, 0.1), transparent 36%),
    linear-gradient(180deg, #f8fafc 0%, #ffffff 70%);
}

.reader-placeholder h3 {
  margin: 0.35rem 0 0;
  font-family: var(--bv-font-serif, Georgia, serif);
  font-size: 1.2rem;
  color: var(--bv-ink, #0b1f2a);
}

.reader-placeholder p {
  margin: 0;
  max-width: 28rem;
  color: var(--bv-ink-muted, #6b8290);
  font-size: 0.92rem;
  line-height: 1.5;
}

.reader-phase {
  margin-top: 0.35rem !important;
  font-size: 0.78rem !important;
  font-weight: 650;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #b45309 !important;
}

.reader-placeholder--failed {
  background:
    radial-gradient(circle at 30% 20%, rgba(192, 54, 44, 0.1), transparent 40%),
    linear-gradient(180deg, #fff8f7 0%, #ffffff 70%);
}

.reader-art {
  position: relative;
  width: 5.5rem;
  height: 4.5rem;
  margin-bottom: 0.35rem;
}

.reader-art__page {
  position: absolute;
  inset: 0.35rem 0.9rem 0.2rem 0.55rem;
  border-radius: 0.35rem;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
}

.reader-art__page--mid {
  inset: 0.2rem 0.7rem 0.35rem 0.75rem;
  opacity: 0.85;
  transform: rotate(-4deg);
}

.reader-art__page--front {
  inset: 0.45rem 0.55rem 0.1rem 1rem;
  transform: rotate(3deg);
  background:
    linear-gradient(#e2e8f0, #e2e8f0) 0.55rem 0.7rem / 58% 0.18rem no-repeat,
    linear-gradient(#e2e8f0, #e2e8f0) 0.55rem 1.15rem / 48% 0.18rem no-repeat,
    linear-gradient(#e2e8f0, #e2e8f0) 0.55rem 1.6rem / 64% 0.18rem no-repeat,
    #ffffff;
}

.reader-art__scan {
  position: absolute;
  left: 0.75rem;
  right: 0.65rem;
  top: 0.7rem;
  height: 0.2rem;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, #1fb8a8, transparent);
  animation: reader-scan 1.8s ease-in-out infinite;
}

.reader-art--failed .reader-art__page {
  inset: 0.4rem 0.85rem;
}

.reader-art__cross {
  position: absolute;
  inset: 1.15rem 1.55rem;
  border-radius: 999px;
  background: rgba(192, 54, 44, 0.12);
}

.reader-art__cross::before,
.reader-art__cross::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 55%;
  height: 0.18rem;
  border-radius: 999px;
  background: #c0362c;
}

.reader-art__cross::before {
  transform: translate(-50%, -50%) rotate(45deg);
}

.reader-art__cross::after {
  transform: translate(-50%, -50%) rotate(-45deg);
}

@keyframes reader-scan {
  0% {
    transform: translateY(0);
    opacity: 0.35;
  }
  50% {
    transform: translateY(2.2rem);
    opacity: 1;
  }
  100% {
    transform: translateY(0);
    opacity: 0.35;
  }
}
</style>
