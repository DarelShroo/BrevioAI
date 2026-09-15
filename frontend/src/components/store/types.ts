export type StoreViewMode = 'grid' | 'table'
export type StoreStatusFilter = 'ALL' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
export type StoreSortField = 'created' | 'name' | 'status' | 'results'

export interface StoreCountSummary {
  ALL: number
  PROCESSING: number
  COMPLETED: number
  FAILED: number
}

export interface StoreSelectOption<T extends string> {
  label: string
  value: T
}
