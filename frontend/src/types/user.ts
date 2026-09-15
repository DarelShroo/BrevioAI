export type JobStatus = 'PROCESSING' | 'COMPLETED' | 'FAILED'

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

export interface UserProfile {
  id: string
  username: string
  email: string
  user_credit: number
  folder_id?: string | null
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
