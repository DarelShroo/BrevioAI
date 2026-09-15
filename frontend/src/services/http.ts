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

export const http: AxiosInstance = axios.create({
  baseURL,
  timeout: 60_000,
  withCredentials: true,
})

function shouldSkipRefresh(url: string): boolean {
  return AUTH_SKIP_REFRESH.some((path) => url.includes(path))
}

let refreshInFlight: Promise<void> | null = null

async function refreshCookies(): Promise<void> {
  if (!refreshInFlight) {
    refreshInFlight = http.post('/auth/refresh').then(() => undefined)
    refreshInFlight.finally(() => {
      refreshInFlight = null
    })
  }
  await refreshInFlight
}

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status || 0
    const config = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const url = String(config?.url || '')

    if (status === 401 && config && !config._retry && !shouldSkipRefresh(url)) {
      config._retry = true
      try {
        await refreshCookies()
        return await http.request(config)
      } catch {
        // Fall through to the original 401.
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
