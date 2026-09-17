import { i18n } from '@/i18n'
import { isBackendPromptLanguage } from '@/i18n/languages'
import type { DataResult, FolderEntry } from '@/types/user'

export type FileKind = 'pdf' | 'docx' | 'audio' | 'video' | 'markdown' | 'text' | 'file'

export function entryId(entry: FolderEntry): string {
  return String(entry.id ?? entry._id ?? '')
}

export function resultId(result: DataResult): string {
  return String(result.id ?? result._id ?? '')
}

const IN_PROGRESS_STATUSES = new Set([
  'PROCESSING',
  'UNKNOWN',
  'QUEUED',
  'TRANSCRIBING',
  'TRANSCRIBED',
  'DIRECT',
  'MAP',
  'REDUCE',
  'FORMAT',
  'FINALIZING',
])

export function normalizeStatus(result: DataResult | undefined): string {
  if (!result) return 'UNKNOWN'
  if (result.status) {
    const status = String(result.status).toUpperCase()
    if (status === 'PROCESSING') {
      const phase = String(result.phase || '').toUpperCase()
      if (phase === 'TRANSCRIBING' || phase === 'TRANSCRIBED') return phase
    }
    return status
  }
  if (result.success === false) return 'FAILED'
  if (result.download_location) return 'COMPLETED'
  return 'PROCESSING'
}

export function entryStatus(entry: FolderEntry): string {
  if (!entry.results?.length) {
    const top = String((entry as { status?: string | null }).status || '').toUpperCase()
    if (top === 'QUEUED') return 'QUEUED'
    if (top === 'FAILED') return 'FAILED'
    if (top === 'COMPLETED') return 'COMPLETED'
    return 'PROCESSING'
  }
  const statuses = entry.results.map((r) => normalizeStatus(r))
  if (statuses.some((s) => IN_PROGRESS_STATUSES.has(s))) {
    if (statuses.includes('QUEUED') && statuses.every((s) => s === 'QUEUED')) {
      return 'QUEUED'
    }
    if (statuses.includes('TRANSCRIBING')) return 'TRANSCRIBING'
    if (statuses.includes('QUEUED')) return 'QUEUED'
    return 'PROCESSING'
  }
  if (statuses.every((s) => s === 'COMPLETED')) return 'COMPLETED'
  if (statuses.every((s) => s === 'FAILED')) return 'FAILED'
  if (statuses.some((s) => s === 'FAILED')) return 'FAILED'
  return 'COMPLETED'
}

export function isTerminalStatus(status: string): boolean {
  const value = status.toUpperCase()
  return value === 'COMPLETED' || value === 'FAILED'
}

export function entryFolderId(entry: FolderEntry): string | null {
  const raw = entry.library_folder_id
  if (!raw) return null
  return String(raw)
}

export function isGenericSourceName(value: string): boolean {
  return /^(document|documento|video)\s*\d*$/i.test(value.trim())
}

export function entryPrimaryName(entry: FolderEntry): string {
  const id = entryId(entry)
  const named = entry.name?.trim()
  if (named && !isGenericSourceName(named) && !isFileDerivedEntryName(entry, named)) {
    return named
  }
  if (id) return i18n.global.t('store.summaryFallback', { id: id.slice(-6) })
  return i18n.global.t('store.untitled')
}

function isFileDerivedEntryName(entry: FolderEntry, name: string): boolean {
  const labels = new Set<string>()
  for (const result of entry.results || []) {
    if (result.name?.trim()) labels.add(result.name.trim())
    if (result.original_name?.trim()) labels.add(result.original_name.trim())
  }
  if (labels.has(name)) return true
  const withoutBatch = name.replace(/\s\(\+\d+\)$/, '').trim()
  if (withoutBatch && labels.has(withoutBatch)) return true

  const original = entry.original_name?.trim()
  if (original) {
    const parts = original.split(';').map((part) => part.trim()).filter(Boolean)
    if (parts.includes(name) || (withoutBatch && parts.includes(withoutBatch))) return true
    if (parts.length > 1 && parts[0] === name) return true
  }
  return false
}

export function completedDownloadableResults(entry: FolderEntry): Array<{ index: number; name: string }> {
  return (entry.results || [])
    .map((result, index) => ({ result, index }))
    .filter(({ result }) => normalizeStatus(result) === 'COMPLETED')
    .map(({ result, index }) => ({
      index: typeof result.index === 'number' ? result.index : index,
      name: result.name || result.original_name || `result-${index + 1}`,
    }))
}

/** True when at least one completed result can be chosen for download. */
export function canDownloadEntry(entry: FolderEntry): boolean {
  return completedDownloadableResults(entry).length >= 1
}

export function uniqueDownloadResultIndex(entry: FolderEntry): number | null {
  const items = completedDownloadableResults(entry)
  return items.length === 1 ? items[0].index : null
}

export function entryResultCount(entry: FolderEntry): number {
  return entry.results?.length || 0
}

export function entryDurationSeconds(entry: FolderEntry): number | null {
  const values = (entry.results || [])
    .map((r) => r.duration)
    .filter((d): d is number => typeof d === 'number' && Number.isFinite(d) && d > 0)
  if (!values.length) return null
  return values.reduce((sum, n) => sum + n, 0)
}

export function formatDuration(seconds: number | null | undefined): string | null {
  if (seconds == null || !Number.isFinite(seconds) || seconds <= 0) return null
  if (seconds < 60) return i18n.global.t('duration.seconds', { n: Math.round(seconds) })
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return secs
    ? i18n.global.t('duration.minutesSeconds', { m: mins, s: secs })
    : i18n.global.t('duration.minutes', { m: mins })
}

export function detectFileKind(filename?: string | null): FileKind {
  const name = String(filename || '').toLowerCase()
  if (name.endsWith('.pdf')) return 'pdf'
  if (name.endsWith('.docx') || name.endsWith('.doc')) return 'docx'
  if (name.endsWith('.mp3') || name.endsWith('.wav') || name.endsWith('.m4a')) return 'audio'
  if (name.endsWith('.mp4')) return 'video'
  if (name.endsWith('.md') || name.endsWith('.markdown')) return 'markdown'
  if (name.endsWith('.txt') || name.endsWith('.text')) return 'text'
  return 'file'
}

export function entryFileKind(entry: FolderEntry): FileKind {
  const names = [entry.name, ...(entry.results || []).map((r) => r.name)]
  for (const name of names) {
    const kind = detectFileKind(name)
    if (kind !== 'file') return kind
  }
  return 'file'
}

export function fileKindIcon(kind: FileKind): string {
  switch (kind) {
    case 'pdf':
      return 'pi pi-file-pdf'
    case 'docx':
      return 'pi pi-file-word'
    case 'audio':
      return 'pi pi-volume-up'
    case 'video':
      return 'pi pi-video'
    case 'markdown':
      return 'pi pi-code'
    case 'text':
      return 'pi pi-file'
    default:
      return 'pi pi-file'
  }
}

export function fileKindLabel(kind: FileKind): string {
  return i18n.global.t(`fileKind.${kind}`)
}

export function entryErrorMessage(entry: FolderEntry): string | null {
  const failed = entry.results?.find((r) => normalizeStatus(r) === 'FAILED')
  if (!failed) return null
  const code = failed.error_code?.trim()
  if (code) {
    const key = `errors.codes.${code}`
    if (i18n.global.te(key)) return String(i18n.global.t(key))
  }
  const raw = failed.error_message || failed.error_type || null
  if (!raw) return null
  return raw.length > 180 ? `${raw.slice(0, 177)}…` : raw
}

export function entryCreatedAt(entry: FolderEntry): Date | null {
  if (entry.created_at) {
    const parsed = new Date(entry.created_at)
    if (!Number.isNaN(parsed.getTime())) return parsed
  }
  const id = entryId(entry)
  if (/^[a-f\d]{24}$/i.test(id)) {
    const seconds = Number.parseInt(id.slice(0, 8), 16)
    if (Number.isFinite(seconds)) return new Date(seconds * 1000)
  }
  return null
}

export function formatEntryDate(entry: FolderEntry): string | null {
  const date = entryCreatedAt(entry)
  if (!date) return null
  return date.toLocaleString(String(i18n.global.locale.value), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function entrySourceLabel(entry: FolderEntry): string {
  const value = String(entry.source_type || '').toLowerCase()
  if (value === 'documents') return i18n.global.t('summary.documents')
  if (value === 'media') return i18n.global.t('summary.media')
  if (value === 'youtube') return i18n.global.t('summary.youtube')
  return fileKindLabel(entryFileKind(entry))
}

export function entryModelLabel(entry: FolderEntry): string | null {
  return entry.model?.trim() || null
}

export function entryLanguageLabel(entry: FolderEntry): string | null {
  const raw = entry.language?.trim()
  if (!raw) return null
  const key = raw.toUpperCase()
  if (isBackendPromptLanguage(key)) return i18n.global.t(`languages.${key}`)
  return raw
}

