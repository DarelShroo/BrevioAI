import { getApiBaseUrl, http } from '@/services/http'

export interface ExampleHighlight {
  summary_match?: string | null
  pdf_ratio?: number
  summary_ratio?: number
}

export interface ExampleEntry {
  id: string
  slug: string
  title: string
  category?: string
  category_key?: string
  style?: string
  style_key?: string
  type?: string
  model?: string
  results?: number
  created_label?: string
  document_name?: string
  summary_level?: string
  summary_level_label?: string
  format?: string
  format_label?: string
  language?: string
  language_label?: string
  default?: boolean
  highlights?: ExampleHighlight[]
  summary_url?: string
  pdf_url?: string
}

export interface ExampleCatalog {
  default_slug: string
  entries: ExampleEntry[]
}

export async function listExamples(): Promise<ExampleCatalog> {
  const { data } = await http.get<ExampleCatalog>('/examples')
  return data
}

export async function getExample(slugOrId: string): Promise<ExampleEntry> {
  const { data } = await http.get<ExampleEntry>(`/examples/${encodeURIComponent(slugOrId)}`)
  return data
}

export async function fetchExampleSummary(slugOrId: string): Promise<string> {
  const { data } = await http.get<string>(`/examples/${encodeURIComponent(slugOrId)}/summary`, {
    responseType: 'text',
    transformResponse: [(body) => body],
  })
  return typeof data === 'string' ? data : String(data ?? '')
}

export function examplePdfUrl(slugOrId: string): string {
  return `${getApiBaseUrl()}/examples/${encodeURIComponent(slugOrId)}/pdf`
}
