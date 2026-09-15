import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth.store'
import { requireAuth, requireGuest } from '@/router/guards'
import * as userService from '@/services/user.service'

vi.mock('@/services/user.service', () => ({
  getMe: vi.fn(),
}))

const profile = {
  id: 'u1',
  username: 'tester1',
  email: 't@example.com',
  user_credit: 0,
  folder_id: null,
}

describe('router auth guards', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(userService.getMe).mockReset()
  })

  it('redirects unauthenticated users to login', async () => {
    vi.mocked(userService.getMe).mockRejectedValueOnce(new Error('unauthenticated'))
    const next = vi.fn()
    await requireAuth({ fullPath: '/store' } as never, {} as never, next)
    expect(next).toHaveBeenCalledWith({ name: 'login', query: { redirect: '/store' } })
  })

  it('allows authenticated users through requireAuth', async () => {
    vi.mocked(userService.getMe).mockResolvedValueOnce(profile as never)
    const next = vi.fn()
    await requireAuth({ fullPath: '/store' } as never, {} as never, next)
    expect(next).toHaveBeenCalledWith()
  })

  it('sends authenticated guests away from login', async () => {
    vi.mocked(userService.getMe).mockResolvedValueOnce(profile as never)
    const next = vi.fn()
    await requireGuest({} as never, {} as never, next)
    expect(next).toHaveBeenCalledWith({ name: 'summary' })
  })
})

describe('router navigation with auth', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(userService.getMe).mockReset()
  })

  it('keeps protected routes behind login', async () => {
    vi.mocked(userService.getMe).mockRejectedValue(new Error('unauthenticated'))
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/login', name: 'login', component: { template: '<div>login</div>' } },
        {
          path: '/store',
          name: 'store',
          component: { template: '<div>store</div>' },
          beforeEnter: requireAuth,
        },
      ],
    })
    await router.push('/store')
    await router.isReady()
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('allows store when the session cookie is valid', async () => {
    vi.mocked(userService.getMe).mockResolvedValue(profile as never)
    setActivePinia(createPinia())
    const auth = useAuthStore()
    await auth.hydrate()
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/login', name: 'login', component: { template: '<div>login</div>' } },
        {
          path: '/store',
          name: 'store',
          component: { template: '<div>store</div>' },
          beforeEnter: requireAuth,
        },
      ],
    })
    await router.push('/store')
    await router.isReady()
    expect(router.currentRoute.value.name).toBe('store')
  })
})
