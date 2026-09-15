export interface ApiEnvelope<T> {
  status: string
  data: T
}

export interface ApiErrorBody {
  detail?: string | Array<{ loc?: unknown[]; msg?: string; type?: string }>
  message?: string
  status?: string
  code?: string
}

export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(message: string, status: number, body?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}
