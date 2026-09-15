import { http, withApiKey } from '@/services/http'
import type { ApiEnvelope } from '@/types/api'
import type {
  CategoryStylesResponse,
  DownloadFormat,
  EstimateDocumentsData,
  LanguagesResponse,
  ModelsResponse,
  OutputFormatsResponse,
  SummaryDestination,
  SummaryFormParams,
  SummaryJobResponse,
  SummaryLevelsResponse,
  TranscriptionProvidersResponse,
  YoutubeSummaryRequest,
} from '@/types/brevio'
import { normalizeModelsPayload, resolveModelId, type ModelsCatalogPayload } from '@/utils/models'

export type { CatalogModel, CatalogProvider, ModelsCatalogPayload } from '@/utils/models'

function appendSummaryFields(
  form: FormData,
  params: SummaryFormParams,
  destination?: SummaryDestination,
): void {
  form.append('language', params.language)
  form.append('model', resolveModelId(params.model) || params.model)
  form.append('category', params.category)
  form.append('style', params.style)
  form.append('format', params.format)
  form.append('summary_level', params.summary_level)
  if (params.reasoning_effort) {
    form.append('reasoning_effort', params.reasoning_effort)
  }
  if (destination?.folder_name?.trim()) {
    form.append('folder_name', destination.folder_name.trim())
  } else if (destination?.library_folder_id) {
    form.append('library_folder_id', destination.library_folder_id)
  }
}

function normalizeFormats(data: OutputFormatsResponse | string[] | unknown): string[] {
  if (Array.isArray(data)) {
    return data.map((item) => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object' && 'value' in (item as object)) {
        return String((item as { value: string }).value)
      }
      return String(item)
    })
  }
  if (data && typeof data === 'object') {
    const typed = data as OutputFormatsResponse
    const list = typed.output_format_types || typed.formats || []
    return normalizeFormats(list)
  }
  return []
}

export async function fetchLanguages(): Promise<string[]> {
  const { data } = await http.get<ApiEnvelope<LanguagesResponse>>(
    '/brevio/languages',
    withApiKey(),
  )
  return data.data.languages || []
}

export async function fetchModels(): Promise<ModelsCatalogPayload> {
  const { data } = await http.get<ApiEnvelope<ModelsResponse | string[]>>(
    '/brevio/models',
    withApiKey(),
  )
  return normalizeModelsPayload(data.data)
}

export async function fetchCategoryStyles(): Promise<CategoryStylesResponse['advanced_content_combinations']> {
  const { data } = await http.get<ApiEnvelope<CategoryStylesResponse>>(
    '/brevio/categories-styles',
    withApiKey(),
  )
  return data.data.advanced_content_combinations || {}
}

export async function fetchOutputFormats(): Promise<string[]> {
  const { data } = await http.get<ApiEnvelope<OutputFormatsResponse | unknown>>(
    '/brevio/output-formats',
    withApiKey(),
  )
  return normalizeFormats(data.data)
}

function normalizeSummaryLevels(data: SummaryLevelsResponse | string[] | unknown): string[] {
  if (Array.isArray(data)) {
    return data.map((item) => (typeof item === 'string' ? item : String(item)))
  }
  if (data && typeof data === 'object') {
    const typed = data as SummaryLevelsResponse
    const list = typed.summary_levels || []
    return list.map((item) => String(item))
  }
  return []
}

export async function fetchSummaryLevels(): Promise<string[]> {
  const { data } = await http.get<ApiEnvelope<SummaryLevelsResponse | unknown>>(
    '/brevio/summary-levels',
    withApiKey(),
  )
  return normalizeSummaryLevels(data.data)
}

export async function fetchTranscriptionProviders(): Promise<TranscriptionProvidersResponse> {
  const { data } = await http.get<ApiEnvelope<TranscriptionProvidersResponse>>(
    '/brevio/transcription-providers',
    withApiKey(),
  )
  return data.data
}

export async function estimateDocuments(
  files: File[],
  params: SummaryFormParams,
  sourceTypes?: string[],
): Promise<EstimateDocumentsData> {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  appendSummaryFields(form, params)
  sourceTypes?.forEach((type) => form.append('source_types', type))
  const { data } = await http.post<ApiEnvelope<EstimateDocumentsData>>(
    '/brevio/estimate-documents',
    form,
  )
  return data.data
}

export async function submitDocuments(
  files: File[],
  params: SummaryFormParams,
  destination?: SummaryDestination,
): Promise<SummaryJobResponse> {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  appendSummaryFields(form, params, destination)
  const { data } = await http.post<SummaryJobResponse>('/brevio/summary-documents', form)
  return data
}

export async function submitMedia(
  files: File[],
  params: SummaryFormParams,
  destination?: SummaryDestination,
): Promise<SummaryJobResponse> {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  appendSummaryFields(form, params, destination)
  if (params.transcription_provider) {
    form.append('transcription_provider', params.transcription_provider)
  }
  if (params.transcription_model) {
    form.append('transcription_model', params.transcription_model)
  }
  const { data } = await http.post<SummaryJobResponse>('/brevio/summary-media', form)
  return data
}

export async function submitYoutubePlaylist(
  payload: YoutubeSummaryRequest,
): Promise<SummaryJobResponse> {
  const {
    transcription_provider: promptTranscription,
    transcription_model: promptTranscriptionModel,
    ...promptConfig
  } = payload.prompt_config
  const { data } = await http.post<SummaryJobResponse>('/brevio/summary-yt-playlist', {
    ...payload,
    prompt_config: promptConfig,
    transcription_provider:
      payload.transcription_provider || promptTranscription || undefined,
    transcription_model:
      payload.transcription_model || promptTranscriptionModel || undefined,
  })
  return data
}

export async function downloadSummary(
  folderEntryId: string,
  format: DownloadFormat = 'md',
  resultIndex = 0,
): Promise<Blob> {
  const { data } = await http.get<Blob>(`/brevio/download/${folderEntryId}`, {
    params: { format, result_index: resultIndex },
    responseType: 'blob',
  })
  return data
}

/** Fetch summary.md as UTF-8 text for the Markdown reader (not a file download). */
export async function fetchSummaryMarkdown(
  folderEntryId: string,
  resultIndex = 0,
): Promise<string> {
  const blob = await downloadSummary(folderEntryId, 'md', resultIndex)
  if (typeof blob.text === 'function') {
    return blob.text()
  }
  return new Response(blob as Blob).text()
}

export function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
