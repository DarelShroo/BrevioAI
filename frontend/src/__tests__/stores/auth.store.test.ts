import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth.store'

vi.mock('@/services/auth.service', () => ({
  login: vi.fn(async () => ({ authenticated: true })),
  register: vi.fn(async () => ({ folder: {}, authenticated: true })),
  logout: vi.fn(async () => undefined),
  refresh: vi.fn(async () => ({ authenticated: true })),
}))

vi.mock('@/services/user.service', () => ({
  getMe: vi.fn(async () => ({
    id: 'abc',
    username: 'tester1',
    email: 't@example.com',
    user_credit: 10,
    folder_id: 'folder-1',
  })),
}))

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('logs in and loads profile from cookie session', async () => {
    const store = useAuthStore()
    await store.login({ identity: 'tester1', password: 'Aa1@aaaa' })
    expect(store.isAuthenticated).toBe(true)
    expect(store.profile?.username).toBe('tester1')
    expect(store.userId).toBe('abc')
  })

  it('logout clears client state', async () => {
    const store = useAuthStore()
    await store.login({ identity: 'tester1', password: 'Aa1@aaaa' })
    await store.logout()
    expect(store.isAuthenticated).toBe(false)
    expect(store.profile).toBeNull()
  })

  it('hydrate returns false without throwing when session is missing', async () => {
    const userService = await import('@/services/user.service')
    vi.mocked(userService.getMe).mockRejectedValueOnce(
      Object.assign(new Error('Refresh token no proporcionado'), {
        name: 'ApiError',
        status: 401,
      }),
    )
    const store = useAuthStore()
    await expect(store.hydrate()).resolves.toBe(false)
    expect(store.isAuthenticated).toBe(false)
    expect(store.profile).toBeNull()
  })

  it('handleSessionExpired clears state and redirects when a session existed', async () => {
    const authService = await import('@/services/auth.service')
    const router = (await import('@/router')).default
    const replace = vi.spyOn(router, 'replace').mockResolvedValue(undefined as never)
    vi.spyOn(router, 'currentRoute', 'get').mockReturnValue({
      value: { name: 'summary', fullPath: '/summary' },
    } as any)

    const store = useAuthStore()
    await store.login({ identity: 'tester1', password: 'Aa1@aaaa' })
    await store.handleSessionExpired()

    expect(store.isAuthenticated).toBe(false)
    expect(store.profile).toBeNull()
    expect(authService.logout).toHaveBeenCalled()
    expect(replace).toHaveBeenCalledWith({
      name: 'login',
      query: { redirect: '/summary' },
    })
  })

  it('handleSessionExpired always redirects to login from any non-auth screen', async () => {
    const authService = await import('@/services/auth.service')
    vi.mocked(authService.logout).mockClear()
    const router = (await import('@/router')).default
    const replace = vi.spyOn(router, 'replace').mockResolvedValue(undefined as never)
    vi.spyOn(router, 'currentRoute', 'get').mockReturnValue({
      value: { name: 'comparar', fullPath: '/comparar' },
    } as any)

    const store = useAuthStore()
    await store.handleSessionExpired()

    expect(store.isAuthenticated).toBe(false)
    expect(authService.logout).toHaveBeenCalled()
    expect(replace).toHaveBeenCalledWith({
      name: 'login',
      query: { redirect: '/comparar' },
    })
  })

  it('handleSessionExpired does not leave the login screen', async () => {
    const router = (await import('@/router')).default
    const replace = vi.spyOn(router, 'replace').mockResolvedValue(undefined as never)
    vi.spyOn(router, 'currentRoute', 'get').mockReturnValue({
      value: { name: 'login', fullPath: '/auth/login' },
    } as any)

    const store = useAuthStore()
    await store.handleSessionExpired()

    expect(replace).not.toHaveBeenCalled()
  })
})
