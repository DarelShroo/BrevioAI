import type { CatalogModel, CatalogProvider } from '@/utils/models'

export interface CategoryStyle {
  style: string
  source_types?: string[]
}

export interface CategoryStylesMap {
  [category: string]: CategoryStyle[]
}

export interface LanguagesResponse {
  languages: string[]
}

export interface ModelsResponse {
  models: string[] | CatalogModel[]
  catalog?: CatalogModel[]
  providers?: CatalogProvider[]
  environment?: string
}

export interface CategoryStylesResponse {
  advanced_content_combinations: CategoryStylesMap
}

export interface OutputFormatsResponse {
  output_format_types?: string[]
  formats?: string[]
}

export interface SummaryLevelsResponse {
  summary_levels: string[]
}

export interface TranscriptionProvider {
  id: string
  implemented: boolean
  user_access: boolean
  requires_api_key: boolean
  access: 'local' | 'pay_per_use'
  display_name: string
}

export interface TranscriptionModel {
  id: string
  provider: string
  vendor_model_id?: string | null
  status: string
  recommended: boolean
  retirement?: string | null
  parameters: string[]
  display_name: string
  requires_api_key: boolean
  user_access: boolean
}

export interface TranscriptionProvidersResponse {
  environment: string
  providers: TranscriptionProvider[]
  models?: TranscriptionModel[]
  selectable: string[]
  default?: string | null
  default_model?: string | null
}

export interface SummaryFormParams {
  language: string
  model: string
  category: string
  style: string
  format: string
  summary_level: string
  transcription_provider?: string
  transcription_model?: string
  reasoning_effort?: string | null
}

export interface ProcessingMessageData {
  message: string
}

export interface SummaryJobResponse {
  status?: string
  data?: ProcessingMessageData
  task_id?: string | null
  folder_entry_id?: string | null
}

export interface YoutubeSummaryRequest {
  prompt_config: SummaryFormParams
  data: Array<{ url: string }>
  library_folder_id?: string | null
  folder_name?: string | null
  transcription_provider?: string | null
  transcription_model?: string | null
}

export interface SummaryDestination {
  library_folder_id?: string | null
  folder_name?: string | null
}

export interface EstimationWarning {
  code: string
  severity: string
  message: string
}

export interface EstimateDocumentsData {
  can_process: boolean
  reason?: string | null
  estimation: {
    input_tokens: {
      prompt_template: number
      documents_content: number
      structural: number
      total: number
    }
    output_tokens: {
      minimum: number
      expected: number
      max_ceiling: number
    }
    total_tokens_worst_case: number
  }
  documents: Array<{
    filename: string
    tokens: number
    extraction: {
      status: string
      pages_total: number
      pages_with_text: number
      pages_without_text: number
    }
  }>
  tokenization: {
    method: string
    confidence: string
    estimated_error_margin: number
  }
  model: {
    name: string
    provider: string
    access?: 'local' | 'pay_per_use'
    requires_api_key?: boolean
    context_limit: number
    max_output_tokens: number
    supports_chunking: boolean
  }
  pricing: {
    model: string
    provider_cost_currency: string
    platform_currency: string
    expected_cost: number
    max_cost: number
    pricing_version: string
  }
  credits: {
    expected: number
    maximum: number
  }
  chunking: {
    required: boolean
    calls: number
  }
  estimation_id: string
  estimated_at: string
  warnings: EstimationWarning[]
}

export type DownloadFormat = 'md' | 'docx' | 'pdf' | 'txt'
