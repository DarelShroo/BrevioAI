import { beforeEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'

describe('http client', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('sends cookies and attaches api key helper', async () => {
    const { http, withApiKey } = await import('@/services/http')
    expect(http.defaults.withCredentials).toBe(true)
    const adapter = vi.fn(async (config: any) => ({
      data: { ok: true },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    }))
    http.defaults.adapter = adapter as any

    await http.get('/users/me')
    expect(adapter).toHaveBeenCalled()
    const config = adapter.mock.calls[0][0]
    expect(config.headers.Authorization).toBeUndefined()

    const keyed = withApiKey({ headers: { 'X-Custom': '1' } })
    expect(keyed.headers?.['X-API-KEY']).toBeTruthy()
    expect((keyed.headers as any)['X-Custom']).toBe('1')
  })

  it('retries once after a successful refresh on 401', async () => {
    const { http } = await import('@/services/http')
    let calls = 0
    http.defaults.adapter = (async (config: any) => {
      calls += 1
      if (String(config.url).includes('/auth/refresh')) {
        return { data: { status: 'success' }, status: 200, statusText: 'OK', headers: {}, config }
      }
      if (!config._retry) {
        return Promise.reject({
          isAxiosError: true,
          message: 'Unauthorized',
          response: { status: 401, data: { detail: 'Expired' } },
          config,
        })
      }
      return { data: { ok: true }, status: 200, statusText: 'OK', headers: {}, config }
    }) as any

    const result = await http.get('/users/me')
    expect(result.status).toBe(200)
    expect(calls).toBeGreaterThanOrEqual(2)
  })

  it('does not refresh on login 401', async () => {
    const { http } = await import('@/services/http')
    const adapter = vi.fn(async (config: any) => {
      return Promise.reject({
        isAxiosError: true,
        message: 'Unauthorized',
        response: { status: 401, data: { detail: 'Invalid credentials' } },
        config,
      })
    })
    http.defaults.adapter = adapter as any

    await expect(http.post('/auth/login', {})).rejects.toMatchObject({
      name: 'ApiError',
      status: 401,
    })
    const urls = adapter.mock.calls.map((call) => String(call[0].url))
    expect(urls.some((url) => url.includes('/auth/refresh'))).toBe(false)
  })

  it('rejects cleanly when refresh fails after a 401', async () => {
    const { http } = await import('@/services/http')
    const unhandled: unknown[] = []
    const onUnhandled = (reason: unknown) => {
      unhandled.push(reason)
    }
    process.on('unhandledRejection', onUnhandled)

    http.defaults.adapter = (async (config: any) => {
      if (String(config.url).includes('/auth/refresh')) {
        return Promise.reject({
          isAxiosError: true,
          message: 'Unauthorized',
          response: { status: 401, data: { detail: 'Refresh token no proporcionado' } },
          config,
        })
      }
      return Promise.reject({
        isAxiosError: true,
        message: 'Unauthorized',
        response: { status: 401, data: { detail: 'Not authenticated' } },
        config,
      })
    }) as any

    try {
      await expect(http.get('/users/me')).rejects.toMatchObject({
        name: 'ApiError',
        status: 401,
        message: 'Not authenticated',
      })
      // Let any floating rejected promises surface before asserting.
      await new Promise((resolve) => setImmediate(resolve))
      expect(unhandled).toEqual([])
    } finally {
      process.off('unhandledRejection', onUnhandled)
    }
  })

  it('stops storming /auth/refresh after a hard failure', async () => {
    const { http, clearSessionRefreshBlock } = await import('@/services/http')
    clearSessionRefreshBlock()
    let refreshCalls = 0
    http.defaults.adapter = (async (config: any) => {
      if (String(config.url).includes('/auth/refresh')) {
        refreshCalls += 1
        return Promise.reject({
          isAxiosError: true,
          message: 'Unauthorized',
          response: { status: 401, data: { detail: 'expired' } },
          config,
        })
      }
      return Promise.reject({
        isAxiosError: true,
        message: 'Unauthorized',
        response: { status: 401, data: { detail: 'Not authenticated' } },
        config,
      })
    }) as any

    await expect(http.get('/users/me')).rejects.toMatchObject({ status: 401 })
    await expect(http.get('/users/folders')).rejects.toMatchObject({ status: 401 })
    expect(refreshCalls).toBe(1)
  })

  it('ends the client session after a failed refresh', async () => {
    const { createPinia, setActivePinia } = await import('pinia')
    setActivePinia(createPinia())
    const { useAuthStore } = await import('@/stores/auth.store')
    const auth = useAuthStore()
    auth.authenticated = true
    auth.profile = {
      id: 'u1',
      username: 'tester1',
      email: 't@example.com',
      user_credit: 0,
      folder_id: null,
    }
    const expired = vi.spyOn(auth, 'handleSessionExpired').mockResolvedValue(undefined)

    const { http, clearSessionRefreshBlock } = await import('@/services/http')
    clearSessionRefreshBlock()
    http.defaults.adapter = (async (config: any) => {
      if (String(config.url).includes('/auth/refresh')) {
        return Promise.reject({
          isAxiosError: true,
          message: 'Unauthorized',
          response: { status: 401, data: { detail: 'expired' } },
          config,
        })
      }
      return Promise.reject({
        isAxiosError: true,
        message: 'Unauthorized',
        response: { status: 401, data: { detail: 'Not authenticated' } },
        config,
      })
    }) as any

    await expect(http.get('/users/me')).rejects.toMatchObject({ status: 401 })
    expect(expired).toHaveBeenCalled()
  })
})

describe('axios identity', () => {
  it('uses axios create', () => {
    expect(axios.create).toBeTypeOf('function')
  })
})
