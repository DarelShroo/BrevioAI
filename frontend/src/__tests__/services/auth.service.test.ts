import { describe, expect, it, vi } from 'vitest'
import * as authService from '@/services/auth.service'
import { http } from '@/services/http'

vi.mock('@/services/http', () => ({
  http: {
    post: vi.fn(),
    get: vi.fn(),
  },
  withApiKey: (config = {}) => config,
}))

describe('auth.service', () => {
  it('posts login payload and returns session data', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: { status: 'success', data: { authenticated: true } },
    } as any)

    const result = await authService.login({ identity: 'u', password: 'p' })
    expect(http.post).toHaveBeenCalledWith('/auth/login', {
      identity: 'u',
      password: 'p',
    })
    expect(result.authenticated).toBe(true)
  })
})
