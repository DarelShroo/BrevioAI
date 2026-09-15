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
})
