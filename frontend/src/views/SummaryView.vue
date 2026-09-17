<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import SummaryParamsForm from '@/components/summary/SummaryParamsForm.vue'
import LibraryFolderField from '@/components/summary/LibraryFolderField.vue'
import FilePicker from '@/components/summary/FilePicker.vue'
import EstimatePanel from '@/components/summary/EstimatePanel.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import StateBlock from '@/components/common/StateBlock.vue'
import { Sparkles } from '@lucide/vue'
import * as brevioService from '@/services/brevio.service'
import * as credentialsService from '@/services/credentials.service'
import { useAppToast } from '@/composables/useToast'
import { useRealtimeStore } from '@/stores/realtime.store'
import { useCatalogStore } from '@/stores/catalog.store'
import { useAuthStore } from '@/stores/auth.store'
import type { DownloadFormat, EstimateDocumentsData, SummaryDestination, SummaryFormParams } from '@/types/brevio'
import { entryId, entryStatus } from '@/utils/entries'
import { parseApiError } from '@/utils/errors'
import {
  canStartProcessing,
  isSummaryModelBlocked,
  isTranscriptionKeyMissing,
} from '@/utils/processingAccess'
import { humanizeId, providerLabel } from '@/utils/labels'
import { isDocumentFile, isMediaFile, isYoutubeUrl } from '@/utils/validation'

const { t, te } = useI18n()
const route = useRoute()
const toast = useAppToast()
const realtime = useRealtimeStore()
const catalog = useCatalogStore()
const auth = useAuthStore()
const activeTab = ref('0')
const submitting = ref(false)
const estimating = ref(false)
const tracking = ref(false)
const formError = ref<string | null>(null)
const estimate = ref<EstimateDocumentsData | null>(null)
const documentFiles = ref<File[]>([])
const mediaFiles = ref<File[]>([])
const youtubeUrl = ref('')
const downloadFormat = ref<DownloadFormat>('md')
const lastFolderEntryId = ref<string | null>(null)
const destination = reactive<SummaryDestination>({
  library_folder_id: typeof route.query.folder === 'string' ? route.query.folder : null,
  folder_name: null,
})

const params = reactive<SummaryFormParams>({
  language: '',
  model: '',
  category: '',
  style: '',
  format: 'markdown',
  summary_level: '',
  transcription_provider: '',
  transcription_model: '',
  reasoning_effort: null,
})
const keyedProviders = ref<Set<string>>(new Set())

const currentEntry = computed(() => realtime.entry(lastFolderEntryId.value))
const currentStatus = computed(() =>
  currentEntry.value ? entryStatus(currentEntry.value) : null,
)
const completedResults = computed(() =>
  (currentEntry.value?.results || []).filter(
    (result) => String(result.status || '').toUpperCase() === 'COMPLETED',
  ),
)
const transcriptionProviderOptions = computed(() =>
  catalog.selectableTranscriptionProviders.map((item) => ({
    label: providerLabel(item.id, t, te),
    value: item.id,
  })),
)
const transcriptionModelOptions = computed(() =>
  catalog.selectableTranscriptionModels
    .filter((item) => !params.transcription_provider || item.provider === params.transcription_provider)
    .map((item) => {
      const base = humanizeId(item.display_name || item.id)
      if (item.status === 'deprecated' || item.status === 'preview') {
        return {
          label: `${base} (${humanizeId(item.status)})`,
          value: item.id,
        }
      }
      return { label: base, value: item.id }
    }),
)
const selectedTranscriptionProvider = computed(() =>
  catalog.selectableTranscriptionProviders.find((item) => item.id === params.transcription_provider),
)
const transcriptionHint = computed(() => {
  const provider = selectedTranscriptionProvider.value
  if (!provider) return null
  if (!provider.requires_api_key) return 'local'
  if (keyedProviders.value.has(provider.id)) return 'byok'
  return 'missing'
})
const summaryBlocked = computed(() =>
  isSummaryModelBlocked(
    catalog.modelById(params.model),
    keyedProviders.value,
    auth.profile?.user_credit ?? 0,
  ),
)
const transcriptionBlocked = computed(() =>
  isTranscriptionKeyMissing(selectedTranscriptionProvider.value, keyedProviders.value),
)
const canSubmitDocuments = computed(() =>
  canStartProcessing({
    summaryBlocked: summaryBlocked.value,
    transcriptionBlocked: false,
    needsTranscription: false,
  }),
)
const canSubmitMedia = computed(() =>
  canStartProcessing({
    summaryBlocked: summaryBlocked.value,
    transcriptionBlocked: transcriptionBlocked.value,
    needsTranscription: true,
  }),
)

const exampleDemoTo = computed(() => ({
  name: 'comparar' as const,
  query: {
    ...(params.category ? { category: params.category } : {}),
    ...(params.style ? { style: params.style } : {}),
    ...(params.model ? { model: params.model } : {}),
    ...(params.summary_level ? { level: params.summary_level } : {}),
  },
}))

onMounted(async () => {
  try {
    await catalog.loadAll()
    if (!params.transcription_provider) {
      params.transcription_provider =
        catalog.defaultTranscriptionProvider || catalog.selectableTranscriptionProviders[0]?.id || ''
    }
    if (!params.transcription_model) {
      const forProvider = catalog.selectableTranscriptionModels.find(
        (item) => item.provider === params.transcription_provider && item.recommended,
      )
      params.transcription_model =
        forProvider?.id ||
        catalog.defaultTranscriptionModel ||
        catalog.selectableTranscriptionModels.find(
          (item) => item.provider === params.transcription_provider,
        )?.id ||
        ''
    }
  } catch {
    /* catalog errors are handled in SummaryParamsForm */
  }
  try {
    const credentials = await credentialsService.listAllCredentials()
    keyedProviders.value = new Set(
      credentials
        .map((item) => item.provider?.trim().toLowerCase())
        .filter((provider): provider is string => Boolean(provider)),
    )
  } catch {
    keyedProviders.value = new Set()
  }
  try {
    await auth.fetchProfile()
  } catch {
    /* credits stay 0 */
  }
})

watch(documentFiles, () => {
  estimate.value = null
})

watch(mediaFiles, () => {
  formError.value = null
})

watch(
  () => params.transcription_provider,
  (provider) => {
    if (!provider) return
    const current = catalog.selectableTranscriptionModels.find(
      (item) => item.id === params.transcription_model,
    )
    if (current?.provider === provider) return
    const next = catalog.selectableTranscriptionModels.find(
      (item) => item.provider === provider && item.recommended,
    )
    params.transcription_model =
      next?.id ||
      catalog.selectableTranscriptionModels.find((item) => item.provider === provider)?.id ||
      ''
  },
)

function resultError(result: { error_code?: string | null; error_message?: string | null; error_type?: string | null }): string | null {
  const code = result.error_code?.trim()
  if (code) {
    const key = `errors.codes.${code}`
    if (te(key)) return String(t(key))
  }
  return result.error_message || result.error_type || null
}

async function watchJob(jobId: string | null | undefined) {
  if (!jobId) return
  lastFolderEntryId.value = jobId
  tracking.value = true
  try {
    await realtime.trackJob(jobId)
  } finally {
    tracking.value = false
  }
}

function paramsReady() {
  return Boolean(
    params.language &&
      params.model &&
      params.category &&
      params.style &&
      params.format &&
      params.summary_level,
  )
}

async function runEstimate() {
  formError.value = null
  estimate.value = null
  if (!documentFiles.value.length) {
    formError.value = t('summary.chooseDocument')
    return
  }
  if (!paramsReady()) {
    formError.value = t('summary.fillParams')
    return
  }
  estimating.value = true
  try {
    estimate.value = await brevioService.estimateDocuments(documentFiles.value, { ...params })
    toast.info(t('summary.estimateReady'))
  } catch (err) {
    formError.value = parseApiError(err)
  } finally {
    estimating.value = false
  }
}

async function submitDocuments() {
  formError.value = null
  if (!documentFiles.value.length) {
    formError.value = t('summary.chooseDocument')
    return
  }
  if (!paramsReady()) {
    formError.value = t('summary.fillParams')
    return
  }
  if (estimate.value && !estimate.value.can_process) {
    formError.value = estimate.value.reason || t('summary.cannotProcess')
    return
  }
  if (!canSubmitDocuments.value) {
    formError.value = t('params.paidBlockedHint')
    return
  }

  submitting.value = true
  try {
    const response = await brevioService.submitDocuments(documentFiles.value, { ...params }, { ...destination })
    lastFolderEntryId.value = response.folder_entry_id || null
    documentFiles.value = []
    estimate.value = null
    toast.success(t('summary.documentJobAccepted'))
    await watchJob(response.folder_entry_id)
  } catch (err) {
    formError.value = parseApiError(err)
  } finally {
    submitting.value = false
  }
}

async function submitMedia() {
  formError.value = null
  if (!mediaFiles.value.length) {
    formError.value = t('summary.chooseMedia')
    return
  }
  if (!paramsReady()) {
    formError.value = t('summary.fillParams')
    return
  }
  if (!canSubmitMedia.value) {
    formError.value = transcriptionBlocked.value
      ? t('summary.transcriptionRequiresKey')
      : t('params.paidBlockedHint')
    return
  }
  submitting.value = true
  try {
    const response = await brevioService.submitMedia(mediaFiles.value, { ...params }, { ...destination })
    lastFolderEntryId.value = response.folder_entry_id || null
    mediaFiles.value = []
    toast.success(t('summary.mediaJobAccepted'))
    await watchJob(response.folder_entry_id)
  } catch (err) {
    formError.value = parseApiError(err)
  } finally {
    submitting.value = false
  }
}

async function submitYoutube() {
  formError.value = null
  if (!isYoutubeUrl(youtubeUrl.value)) {
    formError.value = t('summary.invalidYoutube')
    return
  }
  if (!paramsReady()) {
    formError.value = t('summary.fillParams')
    return
  }
  if (!canSubmitMedia.value) {
    formError.value = transcriptionBlocked.value
      ? t('summary.transcriptionRequiresKey')
      : t('params.paidBlockedHint')
    return
  }
  submitting.value = true
  try {
    await brevioService.submitYoutubePlaylist({
      prompt_config: { ...params },
      transcription_provider: params.transcription_provider,
      transcription_model: params.transcription_model,
      data: [{ url: youtubeUrl.value.trim() }],
      library_folder_id: destination.library_folder_id,
      folder_name: destination.folder_name,
    })
    youtubeUrl.value = ''
    toast.success(t('summary.youtubeJobAccepted'))
  } catch (err) {
    formError.value = parseApiError(err)
  } finally {
    submitting.value = false
  }
}

async function download(resultIndex = 0) {
  const id = lastFolderEntryId.value || (currentEntry.value ? entryId(currentEntry.value) : '')
  if (!id) return
  const result = currentEntry.value?.results?.[resultIndex]
  const baseName = (result?.name || `summary-${resultIndex + 1}`).replace(/\.[^.]+$/, '')
  try {
    const blob = await brevioService.downloadSummary(id, downloadFormat.value, resultIndex)
    brevioService.triggerBrowserDownload(blob, `${baseName}.${downloadFormat.value}`)
    toast.success(t('job.downloadStarted'))
  } catch (err) {
    formError.value = parseApiError(err)
  }
}
</script>

<template>
  <div class="stack summary-view" data-testid="summary-view">
    <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
      <RouterLink :to="exampleDemoTo" data-testid="view-example-btn" custom v-slot="{ navigate, href }">
        <Button :href="href" @click="navigate" severity="info" outlined size="small">
          <Sparkles :size="15" :stroke-width="2.25" style="margin-right: 0.5rem;" aria-hidden="true" />
          {{ t('demo.viewExample') }}
        </Button>
      </RouterLink>
    </div>

    <section class="card-surface panel stack">
      <p class="muted">
        {{ t('summary.intro') }}
      </p>
      <SummaryParamsForm v-model="params" />
      <LibraryFolderField v-model="destination" />
      <Message v-if="summaryBlocked" severity="warn" :closable="false" data-testid="summary-model-blocked">
        <p>{{ t('params.paidBlockedHint') }}</p>
        <RouterLink class="profile-link" :to="{ name: 'profile' }">
          {{ t('summary.openProfile') }}
        </RouterLink>
      </Message>
      <Message v-if="formError" severity="error" :closable="false">{{ formError }}</Message>

      <Tabs v-model:value="activeTab">
        <TabList>
          <Tab value="0">{{ t('summary.documents') }}</Tab>
          <Tab value="1">{{ t('summary.media') }}</Tab>
          <Tab value="2">{{ t('summary.youtube') }}</Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="0">
            <div class="stack tab-body">
              <FilePicker
                v-model:files="documentFiles"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                :hint="t('summary.documentHint')"
                :validator="isDocumentFile"
                :invalid-message="t('summary.invalidDocument')"
              />
              <EstimatePanel :estimate="estimate" />
              <div class="row actions">
                <Button
                  :label="t('summary.estimate')"
                  severity="secondary"
                  :loading="estimating"
                  data-testid="estimate-btn"
                  @click="runEstimate"
                />
                <Button
                  :label="t('summary.submitDocuments')"
                  :loading="submitting"
                  :disabled="!canSubmitDocuments"
                  data-testid="submit-docs-btn"
                  @click="submitDocuments"
                />
              </div>
            </div>
          </TabPanel>
          <TabPanel value="1">
            <div class="stack tab-body">
              <FilePicker
                v-model:files="mediaFiles"
                accept=".mp3,.m4a,.wav,.mp4,audio/mpeg,audio/mp4,audio/wav,video/mp4"
                :hint="t('summary.mediaHint')"
                :validator="isMediaFile"
                :invalid-message="t('summary.invalidMedia')"
              />
              <div v-if="transcriptionProviderOptions.length" class="stack">
                <label for="transcription-provider">{{ t('summary.transcriptionProvider') }}</label>
                <Select
                  input-id="transcription-provider"
                  v-model="params.transcription_provider"
                  :options="transcriptionProviderOptions"
                  option-label="label"
                  option-value="value"
                  :placeholder="t('summary.selectTranscriptionProvider')"
                  class="w-full"
                  data-testid="transcription-provider"
                />
                <label for="transcription-model">{{ t('summary.transcriptionModel') }}</label>
                <Select
                  input-id="transcription-model"
                  v-model="params.transcription_model"
                  :options="transcriptionModelOptions"
                  option-label="label"
                  option-value="value"
                  :placeholder="t('summary.selectTranscriptionModel')"
                  class="w-full"
                  data-testid="transcription-model"
                />
                <p v-if="transcriptionHint === 'local'" class="hint">{{ t('summary.transcriptionLocalHint') }}</p>
                <p v-else-if="transcriptionHint === 'byok'" class="hint">{{ t('summary.transcriptionByokHint') }}</p>
                <p v-else-if="transcriptionHint === 'missing'" class="hint hint-warn">
                  {{ t('summary.transcriptionByokMissing') }}
                </p>
                <Message
                  v-if="transcriptionBlocked"
                  severity="warn"
                  :closable="false"
                  data-testid="transcription-key-required"
                >
                  <p>{{ t('summary.transcriptionRequiresKey') }}</p>
                  <p class="muted">{{ t('summary.transcriptionRequiresKeyHelp') }}</p>
                  <RouterLink class="profile-link" :to="{ name: 'profile' }">
                    {{ t('summary.configureProviderKey') }}
                  </RouterLink>
                </Message>
              </div>
              <Button
                :label="t('summary.submitMedia')"
                :loading="submitting"
                :disabled="!canSubmitMedia"
                data-testid="submit-media-btn"
                @click="submitMedia"
              />
            </div>
          </TabPanel>
          <TabPanel value="2">
            <div class="stack tab-body">
              <label for="yt-url">{{ t('summary.youtubeUrl') }}</label>
              <InputText
                id="yt-url"
                v-model="youtubeUrl"
                placeholder="https://www.youtube.com/playlist?list=..."
                data-testid="yt-url"
              />
              <div v-if="transcriptionProviderOptions.length" class="stack">
                <label for="yt-transcription-provider">{{ t('summary.transcriptionProvider') }}</label>
                <Select
                  input-id="yt-transcription-provider"
                  v-model="params.transcription_provider"
                  :options="transcriptionProviderOptions"
                  option-label="label"
                  option-value="value"
                  :placeholder="t('summary.selectTranscriptionProvider')"
                  class="w-full"
                  data-testid="yt-transcription-provider"
                />
                <label for="yt-transcription-model">{{ t('summary.transcriptionModel') }}</label>
                <Select
                  input-id="yt-transcription-model"
                  v-model="params.transcription_model"
                  :options="transcriptionModelOptions"
                  option-label="label"
                  option-value="value"
                  :placeholder="t('summary.selectTranscriptionModel')"
                  class="w-full"
                  data-testid="yt-transcription-model"
                />
                <p v-if="transcriptionHint === 'local'" class="hint">{{ t('summary.transcriptionLocalHint') }}</p>
                <p v-else-if="transcriptionHint === 'byok'" class="hint">{{ t('summary.transcriptionByokHint') }}</p>
                <p v-else-if="transcriptionHint === 'missing'" class="hint hint-warn">
                  {{ t('summary.transcriptionByokMissing') }}
                </p>
                <Message
                  v-if="transcriptionBlocked"
                  severity="warn"
                  :closable="false"
                  data-testid="yt-transcription-key-required"
                >
                  <p>{{ t('summary.transcriptionRequiresKey') }}</p>
                  <p class="muted">{{ t('summary.transcriptionRequiresKeyHelp') }}</p>
                  <RouterLink class="profile-link" :to="{ name: 'profile' }">
                    {{ t('summary.configureProviderKey') }}
                  </RouterLink>
                </Message>
              </div>
              <Button
                :label="t('summary.submitYoutube')"
                :loading="submitting"
                :disabled="!canSubmitMedia"
                data-testid="submit-yt-btn"
                @click="submitYoutube"
              />
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </section>

    <section class="card-surface panel stack" data-testid="job-status">
      <div class="row head">
        <h2>{{ t('job.status') }}</h2>
        <StatusBadge v-if="currentStatus" :status="currentStatus" />
      </div>
      <StateBlock
        :loading="tracking && !currentEntry"
        :error="null"
        :empty="!currentEntry && !tracking"
        :empty-message="t('job.empty')"
      >
        <div v-if="currentEntry" class="stack">
          <p>
            <strong class="font-serif">{{ currentEntry.name || t('job.untitledEntry') }}</strong>
          </p>
          <p class="muted">{{ t('job.id') }}: {{ entryId(currentEntry) }}</p>
          <ul class="result-list" data-testid="job-results">
            <li v-for="(result, index) in currentEntry.results" :key="index" class="result-row">
              <div class="result-main">
                <span>{{ result.name || t('job.result', { index: index + 1 }) }}</span>
                <StatusBadge :status="result.status" />
                <span v-if="result.phase" class="muted"> · {{ result.phase }}</span>
              </div>
              <span v-if="resultError(result)" class="error">{{ resultError(result) }}</span>
              <Button
                v-if="String(result.status || '').toUpperCase() === 'COMPLETED'"
                :label="t('job.download')"
                icon="pi pi-download"
                size="small"
                text
                data-testid="download-btn"
                @click="download(result.index ?? index)"
              />
            </li>
          </ul>
          <div v-if="completedResults.length" class="row actions">
            <Select
              v-model="downloadFormat"
              :options="['md', 'docx', 'pdf', 'txt']"
              :aria-label="t('job.downloadFormat')"
            />
          </div>
        </div>
      </StateBlock>
    </section>
  </div>
</template>

<style scoped>
.panel {
  padding: var(--bv-space-5);
}

.demo-callout {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0;
  padding: 1.35rem 1.5rem 1.45rem;
  border-radius: 16px;
  border: 0;
  background: linear-gradient(90deg, #042c2c 0%, #063836 48%, #0b4741 100%);
  color: #ffffff;
  box-shadow: 0 10px 28px rgb(4 44 44 / 0.22);
}

.demo-callout__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0 0 0.7rem;
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: #2ab59d;
}

.demo-callout__title {
  margin: 0;
  max-width: 52rem;
  font-size: clamp(1.15rem, 2.1vw, 1.55rem);
  line-height: 1.28;
  font-weight: 700;
  color: #ffffff;
}

.demo-callout__subtitle {
  margin: 0.55rem 0 0;
  max-width: 44rem;
  font-size: 0.95rem;
  line-height: 1.45;
  font-weight: 400;
  color: #ffffff;
}

.demo-callout__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 1.1rem;
  padding: 0.62rem 1.15rem;
  border-radius: 999px;
  background: #2ab59d;
  color: #0a1f1c;
  font-size: 0.9rem;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
  transition: background 140ms ease, transform 140ms ease;
}

.demo-callout__cta:hover {
  background: #34c4ab;
}

.demo-callout__cta:focus-visible {
  outline: 2px solid #9af0df;
  outline-offset: 2px;
}

.tab-body {
  padding-top: var(--bv-space-4);
}

.actions {
  flex-wrap: wrap;
}

.head {
  justify-content: space-between;
}

.error {
  color: var(--bv-danger);
}

.hint {
  margin: 0;
  color: var(--bv-muted, #6b7280);
  font-size: 0.85rem;
}

.hint-warn {
  color: var(--bv-warning, #b45309);
}

.profile-link {
  display: inline-block;
  margin-top: 0.35rem;
  font-weight: 600;
}

ul {
  margin: 0;
  padding-left: 1.1rem;
}

.result-list {
  list-style: none;
  padding-left: 0;
  display: flex;
  flex-direction: column;
  gap: var(--bv-space-3);
}

.result-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--bv-space-2);
  padding: var(--bv-space-3);
  border: 1px solid var(--bv-border);
  border-radius: var(--bv-radius-md);
  background: var(--bv-surface-2, var(--bv-surface));
}

.result-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--bv-space-2);
  min-width: 0;
}
</style>
