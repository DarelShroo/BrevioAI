<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { Filter, FolderOpen, Inbox } from '@lucide/vue'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import StateBlock from '@/components/common/StateBlock.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'
import StoreEntryCard from '@/components/store/StoreEntryCard.vue'
import StoreFolderBar from '@/components/store/StoreFolderBar.vue'
import StoreMetrics from '@/components/store/StoreMetrics.vue'
import StorePager from '@/components/store/StorePager.vue'
import StoreToolbar from '@/components/store/StoreToolbar.vue'
import DownloadResultsDialog from '@/components/store/DownloadResultsDialog.vue'
import SummaryDocumentReader from '@/components/markdown/SummaryDocumentReader.vue'
import type { StoreSortField, StoreStatusFilter, StoreViewMode } from '@/components/store/types'
import * as brevioService from '@/services/brevio.service'
import * as userService from '@/services/user.service'
import { useAppToast } from '@/composables/useToast'
import { useLibraryStore } from '@/stores/library.store'
import { useRealtimeStore } from '@/stores/realtime.store'
import type { DownloadFormat } from '@/types/brevio'
import type { FolderEntry, LibraryFolder } from '@/types/user'
import {
  entryCreatedAt,
  entryDurationSeconds,
  entryErrorMessage,
  entryFileKind,
  entryFolderId,
  entryId,
  entryLanguageLabel,
  entryModelLabel,
  entryPrimaryName,
  entryResultCount,
  entrySourceLabel,
  entryStatus,
  canDownloadEntry,
  fileKindIcon,
  formatDuration,
  formatEntryDate,
  normalizeStatus,
} from '@/utils/entries'
import { parseApiError } from '@/utils/errors'
import { categoryLabel, statusLabel, styleLabel, summaryLevelLabel } from '@/utils/labels'

const { t, te } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useAppToast()
const realtime = useRealtimeStore()
const library = useLibraryStore()
const loading = ref(false)
const error = ref<string | null>(null)
const entries = ref<FolderEntry[]>([])
const filter = ref('')
const statusFilter = ref<StoreStatusFilter>('ALL')
const sortField = ref<StoreSortField>('created')
const viewMode = ref<StoreViewMode>('grid')
const selectedEntryId = ref<string | null>(null)
const detailOpen = ref(false)
const downloadFormat = ref<DownloadFormat>('md')
const downloading = ref(false)
const deleting = ref(false)
const readerResultIndex = ref(0)
const page = ref(0)
const pageSize = ref(12)
const currentScope = ref<'all' | 'unfiled' | string>('all')
const selectedIds = ref<string[]>([])
const downloadDialog = reactive({
  open: false,
  entry: null as FolderEntry | null,
  preferredIndex: null as number | null,
})
const dialog = reactive({
  open: false,
  mode: 'create' as 'create' | 'rename-folder' | 'rename-entry' | 'move',
  name: '',
  targetFolderId: '' as string,
  entryId: '',
  folderId: '',
})

const viewOptions = computed(() => [
  { label: t('store.cards'), value: 'grid' as const },
  { label: t('store.table'), value: 'table' as const },
])

const liveEntries = computed(() => {
  return entries.value.map(entry => {
    const id = entryId(entry)
    return id ? (realtime.entry(id) || entry) : entry
  })
})

const selected = computed(() => {
  if (!selectedEntryId.value) return null
  return liveEntries.value.find(e => entryId(e) === selectedEntryId.value) || null
})

const statusOptions = computed(() => [
  { label: t('store.all'), value: 'ALL' as const },
  { label: t('store.statusProcessing'), value: 'PROCESSING' as const },
  { label: t('store.statusCompleted'), value: 'COMPLETED' as const },
  { label: t('store.statusFailed'), value: 'FAILED' as const },
])

const sortOptions = computed(() => [
  { label: t('store.sortNewest'), value: 'created' as const },
  { label: t('store.sortName'), value: 'name' as const },
  { label: t('store.sortStatus'), value: 'status' as const },
  { label: t('store.sortResults'), value: 'results' as const },
])

const scopedEntries = computed(() => {
  if (currentScope.value === 'all') return liveEntries.value
  if (currentScope.value === 'unfiled') {
    return liveEntries.value.filter((entry) => !entryFolderId(entry))
  }
  return liveEntries.value.filter((entry) => entryFolderId(entry) === currentScope.value)
})

const counts = computed(() => {
  const list = scopedEntries.value
  const base = { ALL: list.length, PROCESSING: 0, COMPLETED: 0, FAILED: 0 }
  for (const entry of list) {
    const status = entryStatus(entry)
    if (status === 'PROCESSING') base.PROCESSING += 1
    else if (status === 'COMPLETED') base.COMPLETED += 1
    else if (status === 'FAILED') base.FAILED += 1
  }
  return base
})

const filtered = computed(() => {
  const q = filter.value.trim().toLowerCase()
  let list = scopedEntries.value.map((entry) => ({
    ...entry,
    id: entryId(entry),
  }))

  if (statusFilter.value !== 'ALL') {
    list = list.filter((entry) => entryStatus(entry) === statusFilter.value)
  }

  if (q) {
    list = list.filter((entry) => {
      const id = entry.id.toLowerCase()
      const name = entryPrimaryName(entry).toLowerCase()
      const status = entryStatus(entry).toLowerCase()
      const kind = entrySourceLabel(entry).toLowerCase()
      const model = (entryModelLabel(entry) || '').toLowerCase()
      const language = (entryLanguageLabel(entry) || '').toLowerCase()
      return (
        id.includes(q) ||
        name.includes(q) ||
        status.includes(q) ||
        kind.includes(q) ||
        model.includes(q) ||
        language.includes(q)
      )
    })
  }

  list.sort((a, b) => {
    if (sortField.value === 'status') {
      return entryStatus(a).localeCompare(entryStatus(b))
    }
    if (sortField.value === 'results') {
      return entryResultCount(b) - entryResultCount(a)
    }
    if (sortField.value === 'created') {
      const aTime = entryCreatedAt(a)?.getTime() ?? 0
      const bTime = entryCreatedAt(b)?.getTime() ?? 0
      return bTime - aTime
    }
    return entryPrimaryName(a).localeCompare(entryPrimaryName(b))
  })

  return list
})

const isEmptyStore = computed(
  () =>
    !loading.value &&
    !error.value &&
    currentScope.value === 'all' &&
    entries.value.length === 0 &&
    !filter.value &&
    statusFilter.value === 'ALL',
)
const isEmptyFolder = computed(
  () =>
    !loading.value &&
    !error.value &&
    currentScope.value !== 'all' &&
    scopedEntries.value.length === 0 &&
    !filter.value &&
    statusFilter.value === 'ALL',
)
const emptyFolderHeading = computed(() =>
  currentScope.value === 'unfiled' ? t('store.unfiledEmpty') : t('store.folderEmpty'),
)
const emptyFolderBody = computed(() =>
  currentScope.value === 'unfiled' ? t('store.unfiledEmptyBody') : t('store.folderEmptyBody'),
)
const isFilteredEmpty = computed(
  () =>
    !loading.value &&
    !error.value &&
    scopedEntries.value.length > 0 &&
    filtered.value.length === 0,
)

const paged = computed(() => {
  const start = page.value * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize.value)))

const selectedCount = computed(() => selectedIds.value.length)

const moveOptions = computed(() => [
  { label: t('store.moveToUnfiled'), value: '' },
  ...library.folders.map((folder) => ({ label: folder.name, value: folder.id })),
])

watch([filter, statusFilter, sortField, viewMode, currentScope], () => {
  page.value = 0
  selectedIds.value = []
})

function canReadSummary(entry: FolderEntry | null, resultIndex = 0): boolean {
  if (!entry?.results?.length) return false
  const result = entry.results[resultIndex] || entry.results[0]
  if (!result) return false
  return normalizeStatus(result) === 'COMPLETED'
}

const activeResult = computed(() => {
  if (!selected.value?.results?.length) return null
  return selected.value.results[readerResultIndex.value] || selected.value.results[0] || null
})

const activeResultName = computed(() => {
  if (!activeResult.value) return ''
  return (
    activeResult.value.name ||
    t('job.result', { index: readerResultIndex.value + 1 })
  )
})

const showResultPhase = computed(() => {
  if (!activeResult.value?.phase) return false
  return normalizeStatus(activeResult.value) !== String(activeResult.value.phase).toUpperCase()
})

const activeResultPhaseLabel = computed(() => {
  return statusLabel(activeResult.value?.phase, t, te)
})

const selectedCategoryLabel = computed(() => {
  return selected.value?.category ? categoryLabel(selected.value.category, t, te) : ''
})

const selectedStyleLabel = computed(() => {
  return selected.value?.style ? styleLabel(selected.value.category, selected.value.style, t, te) : ''
})

const selectedSummaryLevelLabel = computed(() => {
  return selected.value?.summary_level ? summaryLevelLabel(selected.value.summary_level, t, te) : ''
})

function openDetail(entry: FolderEntry, resultIndex = 0) {
  selectedEntryId.value = entryId(entry)
  readerResultIndex.value = resultIndex
  detailOpen.value = true
}

function upsertEntry(item: FolderEntry) {
  const id = entryId(item)
  if (!id) return
  const index = entries.value.findIndex((entry) => entryId(entry) === id)
  if (index >= 0) {
    const next = entries.value.slice()
    next[index] = item
    entries.value = next
  } else {
    entries.value = [item, ...entries.value]
  }
  realtime.upsertEntry(item)
}

function openEntryFromQuery() {
  const raw = route.query.entry
  const id = Array.isArray(raw) ? raw[0] : raw
  if (!id) return
  const found = entries.value.find((entry) => entryId(entry) === id)
  if (found) openDetail(found)
}

function isSelected(entry: FolderEntry) {
  return selectedIds.value.includes(entryId(entry))
}

function toggleSelect(entry: FolderEntry) {
  const id = entryId(entry)
  if (!id) return
  selectedIds.value = isSelected(entry)
    ? selectedIds.value.filter((item) => item !== id)
    : [...selectedIds.value, id]
}

function selectAllVisible() {
  selectedIds.value = filtered.value.map((entry) => entry.id).filter(Boolean)
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const [list] = await Promise.all([userService.listEntries(), library.load().catch(() => undefined)])
    entries.value = list
    list.forEach(item => realtime.upsertEntry(item))
    const valid = new Set(list.map((entry) => entryId(entry)).filter(Boolean))
    selectedIds.value = selectedIds.value.filter((id) => valid.has(id))
    openEntryFromQuery()
  } catch (err) {
    error.value = parseApiError(err)
  } finally {
    loading.value = false
  }
}

function openDownloadDialog(entry: FolderEntry, preferredIndex: number | null = null) {
  if (!canDownloadEntry(entry)) {
    toast.error(t('store.downloadNoneReady'))
    return
  }
  downloadDialog.entry = entry
  downloadDialog.preferredIndex = preferredIndex
  downloadDialog.open = true
}

async function downloadSelectedResults(payload: { indexes: number[]; format: DownloadFormat }) {
  const entry = downloadDialog.entry
  if (!entry || !payload.indexes.length) return
  downloading.value = true
  try {
    for (const resultIndex of payload.indexes) {
      const result = entry.results?.[resultIndex]
      const baseName = (
        result?.name ||
        result?.original_name ||
        entryPrimaryName(entry)
      ).replace(/\.[^.]+$/, '')
      const blob = await brevioService.downloadSummary(entryId(entry), payload.format, resultIndex)
      brevioService.triggerBrowserDownload(blob, `${baseName}.${payload.format}`)
    }
    downloadFormat.value = payload.format
    downloadDialog.open = false
    toast.success(
      t('store.downloadStartedCount', { n: payload.indexes.length }, payload.indexes.length),
    )
  } catch (err) {
    toast.error(parseApiError(err))
  } finally {
    downloading.value = false
  }
}

async function downloadCurrentResult(entry: FolderEntry) {
  openDownloadDialog(entry, readerResultIndex.value)
}

async function removeEntry(entry: FolderEntry) {
  const id = entryId(entry)
  if (!id) return
  const confirmed = window.confirm(t('store.deleteConfirm', { name: entryPrimaryName(entry) }))
  if (!confirmed) return

  deleting.value = true
  try {
    await userService.deleteEntry(id)
    entries.value = entries.value.filter((item) => entryId(item) !== id)
    selectedIds.value = selectedIds.value.filter((item) => item !== id)
    if (selectedEntryId.value === id) {
      detailOpen.value = false
      selectedEntryId.value = null
    }
    toast.success(t('store.entryDeleted'))
    await library.load().catch(() => undefined)
  } catch (err) {
    toast.error(parseApiError(err))
  } finally {
    deleting.value = false
  }
}

function goCreateSummary() {
  const query =
    currentScope.value !== 'all' && currentScope.value !== 'unfiled'
      ? { folder: currentScope.value }
      : undefined
  router.push({ name: 'summary', query })
}

function clearFilters() {
  filter.value = ''
  statusFilter.value = 'ALL'
}

function openCreateFolder() {
  dialog.mode = 'create'
  dialog.name = ''
  dialog.open = true
}

function openRenameFolder(folder: LibraryFolder) {
  dialog.mode = 'rename-folder'
  dialog.folderId = folder.id
  dialog.name = folder.name
  dialog.open = true
}

function openRenameEntry(entry: FolderEntry) {
  dialog.mode = 'rename-entry'
  dialog.entryId = entryId(entry)
  dialog.name = entryPrimaryName(entry)
  dialog.open = true
}

function openMoveDialog() {
  if (!selectedIds.value.length) return
  dialog.mode = 'move'
  dialog.targetFolderId = currentScope.value === 'unfiled' || currentScope.value === 'all' ? '' : currentScope.value
  dialog.open = true
}

const dialogTitle = computed(() => {
  if (dialog.mode === 'create') return t('store.createFolder')
  if (dialog.mode === 'rename-folder') return t('store.renameFolder')
  if (dialog.mode === 'rename-entry') return t('store.renameEntry')
  return t('store.moveDialogTitle')
})

async function submitDialog() {
  try {
    if (dialog.mode === 'create') {
      const name = dialog.name.trim()
      if (!name) {
        toast.error(t('store.nameRequired'))
        return
      }
      await library.create(name)
      toast.success(t('store.folderCreated'))
    } else if (dialog.mode === 'rename-folder') {
      const name = dialog.name.trim()
      if (!name) {
        toast.error(t('store.nameRequired'))
        return
      }
      await library.rename(dialog.folderId, name)
      toast.success(t('store.folderRenamed'))
    } else if (dialog.mode === 'rename-entry') {
      const name = dialog.name.trim()
      if (!name) {
        toast.error(t('store.nameRequired'))
        return
      }
      const updated = await userService.patchEntry(dialog.entryId, { name })
      upsertEntry(updated)
      toast.success(t('store.entryRenamed'))
    } else {
      const result = await userService.moveEntries(selectedIds.value, dialog.targetFolderId || null)
      toast.success(t('store.moved'))
      if (result.failed.length) {
        const code = result.failed[0].code
        toast.error(t(`errors.codes.${code}`))
      }
      selectedIds.value = []
      await load()
    }
    dialog.open = false
  } catch (err) {
    toast.error(parseApiError(err))
  }
}

async function removeFolder(folder: LibraryFolder) {
  const confirmed = window.confirm(t('store.deleteFolderConfirm', { name: folder.name }))
  if (!confirmed) return
  try {
    await library.remove(folder.id)
    for (const entry of entries.value) {
      if (entryFolderId(entry) === folder.id) {
        entry.library_folder_id = null
      }
    }
    currentScope.value = 'all'
    toast.success(t('store.folderDeleted'))
  } catch (err) {
    toast.error(parseApiError(err))
  }
}

async function bulkDelete() {
  if (!selectedIds.value.length) return
  const confirmed = window.confirm(t('store.bulkDeleteConfirm', { n: selectedIds.value.length }))
  if (!confirmed) return
  deleting.value = true
  try {
    const result = await userService.deleteEntries(selectedIds.value)
    const removed = new Set(result.succeeded)
    entries.value = entries.value.filter((item) => !removed.has(entryId(item)))
    selectedIds.value = []
    toast.success(t('store.entriesDeleted'))
    await library.load().catch(() => undefined)
  } catch (err) {
    toast.error(parseApiError(err))
  } finally {
    deleting.value = false
  }
}

onMounted(load)

const stopRealtime = realtime.subscribe((event) => {
  if (event.type === 'summary.progress') return
  void realtime.refreshJob(event.job_id).then((item) => {
    if (item) upsertEntry(item)
    void library.load().catch(() => undefined)
  })
})

watch(
  () => route.query.entry,
  () => {
    openEntryFromQuery()
  },
)

onUnmounted(stopRealtime)
</script>

<template>
  <div class="store-view" data-testid="store-view">
    <header class="hero">
      <p class="eyebrow">
        <FolderOpen :size="14" :stroke-width="2" aria-hidden="true" />
        {{ t('store.eyebrow') }}
      </p>
      <h1 class="font-serif">{{ t('store.title') }}</h1>
      <p class="subtitle">{{ t('store.subtitle') }}</p>
      <StoreMetrics :counts="counts" />
    </header>

    <StoreFolderBar
      :folders="library.folders"
      :unfiled-count="library.unfiledCount"
      :current-scope="currentScope"
      @select="currentScope = $event"
      @create="openCreateFolder"
      @rename="openRenameFolder"
      @remove="removeFolder"
    />

    <StoreToolbar
      v-model:filter="filter"
      v-model:status-filter="statusFilter"
      v-model:sort-field="sortField"
      v-model:view-mode="viewMode"
      :loading="loading"
      :status-options="statusOptions"
      :sort-options="sortOptions"
      :view-options="viewOptions"
      @refresh="load"
    />

    <div v-if="selectedCount" class="bulk-bar" data-testid="store-bulk-bar">
      <span>{{ t('store.selectedCount', { n: selectedCount }) }}</span>
      <div class="row">
        <Button
          :label="t('store.selectAll')"
          size="small"
          text
          data-testid="store-select-all"
          @click="selectAllVisible"
        />
        <Button
          :label="t('store.moveSelected')"
          size="small"
          data-testid="store-move-selected"
          @click="openMoveDialog"
        />
        <Button
          :label="t('store.bulkDelete')"
          size="small"
          severity="danger"
          :loading="deleting"
          data-testid="store-bulk-delete"
          @click="bulkDelete"
        />
      </div>
    </div>

    <section class="board">
      <StateBlock
        :loading="loading && !entries.length"
        :error="error"
        :empty="isEmptyStore || isFilteredEmpty || isEmptyFolder"
        :empty-title="t('store.emptyTitle')"
        :empty-message="t('store.emptyMessage')"
        @retry="load"
      >
        <template #empty>
          <template v-if="isEmptyStore">
            <span class="empty-icon" aria-hidden="true">
              <Inbox :size="28" :stroke-width="1.75" />
            </span>
            <h3>{{ t('store.emptyHeading') }}</h3>
            <p class="muted">{{ t('store.emptyBody') }}</p>
            <Button
              :label="t('store.createSummary')"
              icon="pi pi-plus"
              data-testid="store-empty-cta"
              @click="goCreateSummary"
            />
          </template>
          <template v-else-if="isEmptyFolder">
            <span class="empty-icon" aria-hidden="true">
              <Inbox :size="28" :stroke-width="1.75" />
            </span>
            <h3>{{ emptyFolderHeading }}</h3>
            <p class="muted">{{ emptyFolderBody }}</p>
            <Button
              :label="t('store.createSummary')"
              icon="pi pi-plus"
              data-testid="store-empty-folder-cta"
              @click="goCreateSummary"
            />
          </template>
          <template v-else>
            <span class="empty-icon" aria-hidden="true">
              <Filter :size="28" :stroke-width="1.75" />
            </span>
            <h3>{{ t('store.noMatchTitle') }}</h3>
            <p class="muted">{{ t('store.noMatchBody') }}</p>
            <Button
              :label="t('store.clearFilters')"
              icon="pi pi-times"
              severity="secondary"
              @click="clearFilters"
            />
          </template>
        </template>

        <div v-if="viewMode === 'grid'" data-testid="store-grid">
          <div class="cards-grid">
            <StoreEntryCard
              v-for="entry in paged"
              :key="entry.id"
              :entry="entry"
              :selected="isSelected(entry)"
              :can-download="canDownloadEntry(entry)"
              @open="openDetail(entry)"
              @download="openDownloadDialog(entry)"
              @delete="removeEntry(entry)"
              @toggle-select="toggleSelect(entry)"
            />
          </div>
          <StorePager
            v-if="filtered.length"
            :page="page"
            :total-pages="totalPages"
            :count="filtered.length"
            @prev="page -= 1"
            @next="page += 1"
          />
        </div>

        <DataTable
          v-else
          :value="filtered"
          data-key="id"
          striped-rows
          paginator
          :rows="8"
          responsive-layout="scroll"
          data-testid="store-table"
        >
          <Column>
            <template #body="{ data }">
              <input
                type="checkbox"
                :checked="isSelected(data)"
                data-testid="store-entry-select"
                :aria-label="entryPrimaryName(data)"
                @change="toggleSelect(data)"
              />
            </template>
          </Column>
          <Column :header="t('store.document')">
            <template #body="{ data }">
              <div class="doc-cell">
                <i
                  :class="fileKindIcon(entryFileKind(data))"
                  :title="entrySourceLabel(data)"
                  aria-hidden="true"
                />
                <div>
                  <strong class="font-serif">{{ entryPrimaryName(data) }}</strong>
                  <p class="muted tiny">{{ entrySourceLabel(data) }}</p>
                </div>
              </div>
            </template>
          </Column>
          <Column :header="t('store.created')">
            <template #body="{ data }">
              {{ formatEntryDate(data) || '—' }}
            </template>
          </Column>
          <Column :header="t('store.model')">
            <template #body="{ data }">
              {{ entryModelLabel(data) || '—' }}
            </template>
          </Column>
          <Column :header="t('store.status')">
            <template #body="{ data }">
              <StatusBadge v-if="entryStatus(data) !== 'PROCESSING' || data.progress == null" :status="entryStatus(data)" />
              <ProgressBar v-else :progress="data.progress || 0" :stage="data.stage" :status="data.status" :show-labels="false" style="width: 100px;" />
            </template>
          </Column>
          <Column :header="t('store.results')">
            <template #body="{ data }">
              {{ entryResultCount(data) }}
            </template>
          </Column>
          <Column :header="t('store.duration')">
            <template #body="{ data }">
              {{ formatDuration(entryDurationSeconds(data)) || '—' }}
            </template>
          </Column>
          <Column :header="t('store.actions')">
            <template #body="{ data }">
              <div class="row">
                <Button
                  icon="pi pi-eye"
                  size="small"
                  text
                  v-tooltip.top="t('store.openDetails')"
                  :aria-label="t('store.openDetails')"
                  data-testid="store-view-btn"
                  @click="openDetail(data)"
                />
                <Button
                  v-if="canDownloadEntry(data)"
                  icon="pi pi-download"
                  size="small"
                  text
                  v-tooltip.top="t('store.download')"
                  :aria-label="t('store.download')"
                  data-testid="store-download-btn"
                  @click="openDownloadDialog(data)"
                />
                <Button
                  icon="pi pi-pencil"
                  size="small"
                  text
                  v-tooltip.top="t('store.renameEntry')"
                  :aria-label="t('store.renameEntry')"
                  data-testid="store-rename-entry"
                  @click="openRenameEntry(data)"
                />
                <Button
                  icon="pi pi-trash"
                  size="small"
                  text
                  severity="danger"
                  :loading="deleting"
                  v-tooltip.top="t('store.delete')"
                  :aria-label="t('store.deleteEntry')"
                  data-testid="store-delete-btn"
                  @click="removeEntry(data)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </StateBlock>
    </section>

    <Drawer
      v-model:visible="detailOpen"
      position="right"
      class="detail-drawer"
      :block-scroll="true"
    >
      <template #header>
        <div class="drawer-header">
          <i v-if="selected" :class="fileKindIcon(entryFileKind(selected))" aria-hidden="true" />
          <span>{{ t('store.entryDetail') }}</span>
        </div>
      </template>

      <div v-if="selected" class="detail-shell" data-testid="store-detail">
        <div class="detail-scroll">
          <div class="detail-title">
            <h3 class="font-serif">{{ entryPrimaryName(selected) }}</h3>
            <p class="muted tiny">{{ t('job.id') }}: {{ entryId(selected) }}</p>
            <StatusBadge v-if="entryStatus(selected) !== 'PROCESSING' || selected.progress == null" :status="entryStatus(selected)" />
            <ProgressBar v-else :progress="selected.progress || 0" :stage="selected.stage" :status="selected.status" :show-labels="true" />
          </div>

          <div class="meta-grid">
            <div>
              <span class="meta-key">{{ t('store.type') }}</span>
              <strong class="meta-val">{{ entrySourceLabel(selected) }}</strong>
            </div>
            <div>
              <span class="meta-key">{{ t('store.created') }}</span>
              <strong class="meta-val">{{ formatEntryDate(selected) || '—' }}</strong>
            </div>
            <div>
              <span class="meta-key">{{ t('store.language') }}</span>
              <strong class="meta-val">{{ entryLanguageLabel(selected) || '—' }}</strong>
            </div>
            <div>
              <span class="meta-key">{{ t('store.model') }}</span>
              <strong class="meta-val">{{ entryModelLabel(selected) || '—' }}</strong>
            </div>
            <div>
              <span class="meta-key">{{ t('store.results') }}</span>
              <strong class="meta-val">{{ entryResultCount(selected) }}</strong>
            </div>
            <div>
              <span class="meta-key">{{ t('store.duration') }}</span>
              <strong class="meta-val">{{ formatDuration(entryDurationSeconds(selected)) || '—' }}</strong>
            </div>
            <div v-if="selected.category">
              <span class="meta-key">{{ t('store.category') }}</span>
              <strong class="meta-val">{{ selectedCategoryLabel }}</strong>
            </div>
            <div v-if="selected.style">
              <span class="meta-key">{{ t('store.style') }}</span>
              <strong class="meta-val">{{ selectedStyleLabel }}</strong>
            </div>
            <div v-if="selected.summary_level">
              <span class="meta-key">{{ t('store.level') }}</span>
              <strong class="meta-val">{{ selectedSummaryLevelLabel }}</strong>
            </div>
          </div>

          <p v-if="entryErrorMessage(selected)" class="error">{{ entryErrorMessage(selected) }}</p>
        </div>

        <div v-if="selected.results?.length" class="active-doc card-surface" data-testid="store-active-doc">
          <div class="active-doc__main">
            <span class="active-doc__label">{{ t('store.summaryReader') }}</span>
            <strong class="active-doc__name" :title="activeResultName">{{ activeResultName }}</strong>
            <div class="active-doc__meta">
              <StatusBadge v-if="activeResult && (normalizeStatus(activeResult) !== 'PROCESSING' || activeResult.progress == null)" :status="normalizeStatus(activeResult)" />
              <ProgressBar v-else-if="activeResult" :progress="activeResult.progress || 0" :stage="activeResult.phase" :status="activeResult.status" :show-labels="true" />
              <span v-if="showResultPhase" class="muted tiny">{{ activeResultPhaseLabel }}</span>
              <span v-if="selected.results.length > 1" class="muted tiny">
                {{ readerResultIndex + 1 }}/{{ selected.results.length }}
              </span>
            </div>
          </div>
          <div class="active-doc__actions">
            <Select
              v-if="selected.results.length > 1"
              v-model="readerResultIndex"
              :options="
                selected.results.map((result, index) => ({
                  label: result.name || t('store.result', { index: index + 1 }),
                  value: result.index ?? index,
                }))
              "
              option-label="label"
              option-value="value"
              class="result-select"
              data-testid="store-result-select"
            />
            <Button
              v-if="canReadSummary(selected, readerResultIndex)"
              icon="pi pi-download"
              size="small"
              text
              :loading="downloading"
              v-tooltip.top="t('store.downloadResult')"
              :aria-label="t('store.downloadAria')"
              @click="openDownloadDialog(selected, readerResultIndex)"
            />
          </div>
          <p v-if="activeResult?.error_message" class="error active-doc__error">
            {{ activeResult.error_message }}
          </p>
        </div>
        <p v-else class="muted active-doc-empty">{{ t('store.noResults') }}</p>

        <div v-if="selected.results?.length" class="detail-reader">
          <SummaryDocumentReader
            :folder-entry-id="entryId(selected)"
            :result-index="readerResultIndex"
            :status="normalizeStatus(activeResult || undefined)"
            :phase="activeResult?.phase || null"
          />
        </div>
        <div v-else class="detail-reader detail-reader--empty">
          <p class="muted">{{ t('store.noResults') }}</p>
        </div>

        <footer class="detail-footer">
          <div class="detail-footer__format">
            <Button
              :label="t('store.download')"
              icon="pi pi-download"
              size="small"
              outlined
              :loading="downloading"
              :disabled="!canDownloadEntry(selected)"
              v-tooltip.top="t('store.downloadPickHint')"
              :aria-label="t('store.downloadAria')"
              data-testid="store-detail-download"
              @click="downloadCurrentResult(selected)"
            />
          </div>
          <div class="detail-footer__actions">
            <Button
              :label="t('store.renameEntry')"
              icon="pi pi-pencil"
              outlined
              class="btn-rename"
              data-testid="store-detail-rename"
              @click="openRenameEntry(selected)"
            />
            <Button
              :label="t('store.deleteEntry')"
              icon="pi pi-trash"
              outlined
              severity="danger"
              class="btn-delete"
              :loading="deleting"
              data-testid="store-detail-delete"
              @click="removeEntry(selected)"
            />
          </div>
        </footer>
      </div>
    </Drawer>

    <DownloadResultsDialog
      v-model:visible="downloadDialog.open"
      :entry="downloadDialog.entry"
      :preferred-index="downloadDialog.preferredIndex"
      :initial-format="downloadFormat"
      :loading="downloading"
      @confirm="downloadSelectedResults"
    />

    <Dialog
      v-model:visible="dialog.open"
      modal
      :header="dialogTitle"
      :style="{ width: 'min(28rem, 92vw)' }"
    >
      <div class="stack dialog-body">
        <template v-if="dialog.mode === 'move'">
          <label for="move-folder">{{ t('store.moveTo') }}</label>
          <Select
            input-id="move-folder"
            v-model="dialog.targetFolderId"
            :options="moveOptions"
            option-label="label"
            option-value="value"
            data-testid="store-move-select"
            class="w-full"
          />
        </template>
        <template v-else>
          <label for="folder-name-input">{{ t('store.renamePlaceholder') }}</label>
          <InputText
            id="folder-name-input"
            v-model="dialog.name"
            :placeholder="
              dialog.mode === 'create' ? t('store.newFolderPlaceholder') : t('store.renamePlaceholder')
            "
            class="w-full"
            data-testid="store-name-input"
          />
        </template>
        <div class="row" style="justify-content: flex-end">
          <Button :label="t('common.cancel')" text @click="dialog.open = false" />
          <Button
            :label="t('common.save')"
            data-testid="store-dialog-save"
            @click="submitDialog"
          />
        </div>
      </div>
    </Dialog>
  </div>
</template>

<style scoped>
.hero {
  padding: 0.35rem 0 1.5rem;
}

.hero h1 {
  margin: 0.25rem 0 0;
  font-family: var(--bv-font-serif);
  font-optical-sizing: auto;
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  margin: 0;
  font-size: 0.75rem;
  font-weight: 600;
  color: #0f766e;
}

.subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: #64748b;
}

.board {
  padding: 0;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  gap: 1rem;
}

.doc-cell {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.doc-cell i {
  color: #0f766e;
  font-size: 1.15rem;
}

.tiny {
  font-size: 0.8rem;
  margin: 0;
}

.empty-icon {
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: #14b8a6;
  background: #f0fdfa;
  margin-bottom: 0.5rem;
}

.detail-shell {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  flex: 1 1 auto;
}

.detail-scroll {
  flex: 0 1 auto;
  max-height: min(28vh, 14rem);
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0.25rem 1.75rem 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.active-doc {
  flex: 0 0 auto;
  position: relative;
  z-index: 3;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1rem;
  margin: 0 1.25rem 0.65rem;
  padding: 0.85rem 1rem;
  background: #ffffff;
  box-shadow: 0 1px 2px rgb(15 23 42 / 0.04);
}

.active-doc-empty {
  flex: 0 0 auto;
  margin: 0 1.25rem 0.65rem;
}

.detail-reader {
  flex: 1 1 0;
  min-height: 12rem;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 0 1.25rem 0.75rem;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.detail-reader--empty {
  align-items: center;
  justify-content: center;
}

.detail-footer {
  flex-shrink: 0;
  position: relative;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.85rem;
  padding: 0.85rem 1.25rem;
  border-top: 1px solid #e2e8f0;
  background: color-mix(in srgb, #ffffff 95%, transparent);
  backdrop-filter: blur(8px);
}

.detail-title {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.detail-title h3 {
  margin: 0;
  font-family: var(--bv-font-serif);
  font-optical-sizing: auto;
  font-size: 1.45rem;
  color: var(--bv-ink);
}

.result-actions {
  gap: 0.25rem;
}

.active-doc__main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem 0.75rem;
  min-width: 0;
  flex: 1 1 14rem;
}

.active-doc__label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}

.active-doc__name {
  min-width: 0;
  font-size: 0.92rem;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: min(100%, 28rem);
}

.active-doc__meta {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}

.active-doc__actions {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.active-doc__error {
  flex: 1 1 100%;
  margin: 0;
}

.result-select {
  min-width: 10rem;
  max-width: 16rem;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid #e2e8f0;
}

.meta-grid > div {
  min-width: 0;
}

.meta-key {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
}

.meta-val {
  display: block;
  margin-top: 0.2rem;
  font-size: 0.875rem;
  font-weight: 650;
  color: #0f172a;
  overflow-wrap: anywhere;
}

.result-item {
  padding: 0.75rem;
}

.error {
  color: var(--bv-danger);
  margin: 0;
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.detail-footer__format {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
}

.detail-footer__format label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #64748b;
}

.detail-footer__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem;
  margin-left: auto;
}

.bulk-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin: 0 0 1rem;
  padding: 0.65rem 0.85rem;
  border: 1px solid #99f6e4;
  background: #f0fdfa;
  border-radius: 0.75rem;
  color: #0f766e;
  font-size: 0.875rem;
  font-weight: 600;
}

.dialog-body {
  gap: 0.75rem;
}

@media (min-width: 640px) {
  .meta-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 768px) {
  .cards-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .meta-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (min-width: 1280px) {
  .cards-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .detail-scroll {
    padding: 0.25rem 1rem 0.85rem;
    max-height: min(26vh, 12rem);
  }

  .active-doc {
    margin: 0 0.85rem 0.55rem;
  }

  .active-doc-empty {
    margin: 0 0.85rem 0.55rem;
  }

  .detail-reader {
    min-height: 0;
    padding: 0 0.85rem 0.65rem;
  }

  .detail-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .detail-footer__actions {
    margin-left: 0;
    width: 100%;
  }

  .detail-footer__actions :deep(.p-button) {
    flex: 1;
  }
}
</style>

<!-- Teleported Drawer leaves StoreView DOM; unscoped rules required for panel chrome. -->
<style>
.p-drawer.detail-drawer {
  width: 100vw !important;
  max-width: 100vw !important;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.28);
  background: #ffffff;
}

.p-drawer.detail-drawer .p-drawer-header {
  flex-shrink: 0;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.p-drawer.detail-drawer .p-drawer-content {
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

@media (min-width: 1024px) {
  .p-drawer.detail-drawer {
    width: 80vw !important;
    max-width: 80vw !important;
  }
}

@media (min-width: 1280px) {
  .p-drawer.detail-drawer {
    width: min(70vw, 72rem) !important;
    max-width: min(70vw, 72rem) !important;
  }
}
</style>
