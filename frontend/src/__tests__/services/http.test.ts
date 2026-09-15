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
})

describe('axios identity', () => {
  it('uses axios create', () => {
    expect(axios.create).toBeTypeOf('function')
  })
})
