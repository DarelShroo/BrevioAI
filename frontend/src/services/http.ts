import axios, { type AxiosInstance, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import { i18n } from '@/i18n'
import { ApiError } from '@/types/api'
import { messageFromApiBody, extractDetail } from '@/utils/errors'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const apiKey = import.meta.env.VITE_API_KEY || ''

const AUTH_SKIP_REFRESH = [
  '/auth/login',
  '/auth/register',
  '/auth/refresh',
  '/auth/logout',
  '/auth/password-recovery-handshake',
  '/auth/password-recovery-verify',
]

type AuthRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean
  skipSessionExpired?: boolean
}

export const http: AxiosInstance = axios.create({
  baseURL,
  timeout: 60_000,
  withCredentials: true,
})

function shouldSkipRefresh(url: string): boolean {
  return AUTH_SKIP_REFRESH.some((path) => url.includes(path))
}

let refreshInFlight: Promise<void> | null = null
/** After a hard refresh failure, stop calling /auth/refresh until login succeeds. */
let refreshBlocked = false

export function clearSessionRefreshBlock(): void {
  refreshBlocked = false
}

function errorStatus(error: unknown): number {
  if (!error || typeof error !== 'object') return 0
  if ('response' in error) {
    const status = (error as { response?: { status?: number } }).response?.status
    if (typeof status === 'number') return status
  }
  if ('status' in error && typeof (error as { status?: number }).status === 'number') {
    return (error as { status: number }).status
  }
  return 0
}

async function refreshCookies(): Promise<void> {
  if (refreshBlocked) {
    const err = new Error('Session refresh unavailable') as Error & {
      response?: { status: number }
      status?: number
    }
    err.response = { status: 401 }
    err.status = 401
    throw err
  }
  if (!refreshInFlight) {
    // Chain finally onto the same promise that callers await so a failed
    // refresh cannot surface as an unhandled rejection (e.g. guest hydrate).
    refreshInFlight = http
      .post('/auth/refresh')
      .then(() => {
        refreshBlocked = false
      })
      .catch((error: unknown) => {
        const status = errorStatus(error)
        // Dead session or rate-limited refresh — do not storm the auth bucket.
        if (status === 401 || status === 403 || status === 429) {
          refreshBlocked = true
        }
        throw error
      })
      .finally(() => {
        refreshInFlight = null
      })
  }
  await refreshInFlight
}

async function notifySessionExpired(): Promise<void> {
  try {
    const { useAuthStore } = await import('@/stores/auth.store')
    await useAuthStore().handleSessionExpired()
  } catch {
    // Pinia may not be ready in unit tests; ignore.
  }
}

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status || 0
    const config = error.config as AuthRequestConfig | undefined
    const url = String(config?.url || '')
    const skipSessionExpired = config?.skipSessionExpired === true

    if (status === 401 && config && !shouldSkipRefresh(url)) {
      if (!config._retry) {
        config._retry = true
        try {
          await refreshCookies()
          return await http.request(config)
        } catch {
          if (!skipSessionExpired) {
            // Refresh cookie missing/invalid — force login from any screen.
            await notifySessionExpired()
          }
        }
      } else if (!skipSessionExpired) {
        // Still unauthorized after a successful refresh rotation.
        await notifySessionExpired()
      }
    }

    const message =
      messageFromApiBody(error.response?.data) ||
      extractDetail(error.response?.data) ||
      error.message ||
      i18n.global.t('errors.fallback')
    return Promise.reject(new ApiError(message, status, error.response?.data))
  },
)

export function withApiKey(config: AxiosRequestConfig = {}): AxiosRequestConfig {
  return {
    ...config,
    headers: {
      ...(config.headers || {}),
      'X-API-KEY': apiKey,
    },
  }
}

export function getApiBaseUrl(): string {
  return baseURL
}
