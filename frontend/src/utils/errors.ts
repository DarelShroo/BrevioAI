import { i18n } from '@/i18n'
import type { ApiErrorBody } from '@/types/api'
import { ApiError } from '@/types/api'
import type { AxiosError } from 'axios'

export function parseApiError(error: unknown, fallback?: string): string {
  const resolvedFallback = fallback || i18n.global.t('errors.fallback')
  if (error instanceof ApiError) {
    return messageFromApiBody(error.body) || error.message || resolvedFallback
  }

  if (isAxiosError(error)) {
    const status = error.response?.status
    if (!error.response) {
      return i18n.global.t('errors.backendUnavailable')
    }
    const detail = messageFromApiBody(error.response.data)
    if (detail) return detail
    if (status === 401) return i18n.global.t('errors.invalidCredentials')
    if (status === 404) return i18n.global.t('errors.notFound')
    if (status === 422) return i18n.global.t('errors.validationFailed')
    return error.message || resolvedFallback
  }

  if (error instanceof Error) {
    return error.message || resolvedFallback
  }

  return resolvedFallback
}

export function messageFromApiBody(body: unknown): string | null {
  const code = extractErrorCode(body)
  if (code) {
    const key = `errors.codes.${code}`
    if (i18n.global.te(key)) {
      return String(i18n.global.t(key))
    }
  }
  return extractDetail(body)
}

export function extractErrorCode(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const data = body as ApiErrorBody
  if (typeof data.code === 'string' && data.code.trim()) {
    return data.code.trim()
  }
  return null
}

function isStackTrace(str: string): boolean {
  return str.includes('Traceback') || str.includes('\n  File ') || str.includes('\n    at ')
}

export function extractDetail(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const data = body as ApiErrorBody

  if (typeof data.detail === 'string' && data.detail.trim()) {
    if (isStackTrace(data.detail)) return null
    return data.detail
  }

  if (Array.isArray(data.detail) && data.detail.length > 0) {
    const messages = data.detail
      .map((item) => item.msg || JSON.stringify(item))
      .filter((msg) => msg && !isStackTrace(msg))
    if (messages.length > 0) {
      return messages.join('; ')
    }
  }

  if (typeof data.message === 'string' && data.message.trim()) {
    if (isStackTrace(data.message)) return null
    return data.message
  }

  return null
}

function isAxiosError(error: unknown): error is AxiosError {
  return Boolean(error && typeof error === 'object' && (error as AxiosError).isAxiosError)
}
