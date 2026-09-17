export type JobStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

export interface DataResult {
  id?: string
  _id?: string
  index?: number | null
  url?: string | null
  download_location?: string | null
  name?: string | null
  original_name?: string | null
  duration?: number | null
  status?: JobStatus | string | null
  phase?: string | null
  success?: boolean | null
  error_type?: string | null
  error_code?: string | null
  error_message?: string | null
  progress?: number
  stage_progress?: number
  weight?: number
}

export interface FolderEntry {
  id?: string
  _id?: string
  user_id: string
  name: string
  original_name?: string | null
  library_folder_id?: string | null
  results: DataResult[]
  created_at?: string | null
  updated_at?: string | null
  language?: string | null
  model?: string | null
  category?: string | null
  style?: string | null
  format?: string | null
  summary_level?: string | null
  /** documents | media | youtube */
  source_type?: string | null
  /** Job-level status (QUEUED/PROCESSING/COMPLETED/FAILED). */
  status?: JobStatus | string | null
  progress?: number
  stage?: string | null
}

export interface LibraryFolder {
  id: string
  name: string
  created_at?: string
  updated_at?: string
  entry_count: number
}

export interface ListLibraryFoldersResponse {
  folders: LibraryFolder[]
  unfiled_count: number
}

export interface BulkEntriesResponse {
  succeeded: string[]
  failed: Array<{ id: string; code: string }>
}

export interface PlanEntitlements {
  plan_id: string
  plan_name: string
  plan_version: string
  period_start: string
  period_end: string
  period_mode?: string
  rolling_days?: number
  plan_change_usage_policy?: string
  limits: {
    documents_per_period: number
    pages_per_document: number
    pages_per_period: number
    bytes_per_document: number
    bytes_per_audio?: number
    bytes_per_video?: number
    bytes_per_period: number
    credits_per_period: number
    rollover_max?: number
    max_concurrent_jobs: number
    media_enabled: boolean
    youtube_enabled: boolean
    byok_allowed: boolean
    retention_days?: number
    brevio_funded_models?: string[]
    funds_all_models?: boolean
  }
  usage: {
    documents_used: number
    pages_used: number
    bytes_used: number
    credits_used: number
    concurrent_jobs: number
  }
  remaining: {
    documents: number
    pages: number
    bytes: number
    credits: number
    concurrent_jobs: number
  }
}

export interface PlanCatalogItem {
  plan_id: string
  name: string
  version: string
  status: string
  documents_per_period: number
  pages_per_document: number
  pages_per_period: number
  bytes_per_document: number
  bytes_per_audio: number
  bytes_per_video: number
  bytes_per_period: number
  credits_per_period: number
  rollover_max: number
  max_concurrent_jobs: number
  scheduler_weight: number
  scheduler_priority: number
  byok_allowed: boolean
  brevio_funded_models: string[]
  funds_all_models: boolean
  retention_days: number
  media_enabled: boolean
  youtube_enabled: boolean
  price_amount: number | null
  annual_price_amount?: number | null
  price_currency: string | null
  billing_interval: string | null
  highlighted?: boolean
  cta_kind?: string
  trial_days?: number | null
}

export interface PlansCatalog {
  status: string
  default_plan_id: string
  period_mode: string
  rolling_days: number
  plan_change_usage_policy: string
  checkout_enabled: boolean
  billing_provider: string | null
  customer_portal_enabled: boolean
  show_billing_toggle?: boolean
  annual_discount_percent?: number
  sales_email?: string | null
  highlighted_plan_id?: string | null
  plans: PlanCatalogItem[]
}

export interface UserProfile {
  id: string
  username: string
  email: string
  user_credit: number
  folder_id?: string | null
  plan_id?: string
  plan_name?: string
  plan_version?: string
  entitlements?: PlanEntitlements | null
}

export interface GetEntriesResponse {
  entries: FolderEntry[]
}

export interface EntriesPollRequest {
  entries_refs: string[]
}

export interface UserCredential {
  id: string
  _id?: string
  user_id: string
  provider: string
  name: string
  is_default: boolean
  status: string
  created_at: string
  updated_at: string
}

export interface CredentialCreateRequest {
  provider: string
  api_key: string
  name: string
  is_default?: boolean
}

export interface CredentialUpdateRequest {
  name: string
}
