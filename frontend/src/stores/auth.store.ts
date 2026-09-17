import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authService from '@/services/auth.service'
import { clearSessionRefreshBlock } from '@/services/http'
import type { LoginRequest, RegisterRequest } from '@/types/auth'
import type { UserProfile } from '@/types/user'
import * as userService from '@/services/user.service'

export const useAuthStore = defineStore('auth', () => {
  const authenticated = ref(false)
  const profile = ref<UserProfile | null>(null)
  const loading = ref(false)
  let hydratePromise: Promise<boolean> | null = null
  let sessionExpiryPromise: Promise<void> | null = null

  const isAuthenticated = computed(() => authenticated.value)
  const userId = computed(() => profile.value?.id ?? null)

  async function fetchProfile() {
    profile.value = await userService.getMe()
    authenticated.value = true
    return profile.value
  }

  async function login(payload: LoginRequest) {
    loading.value = true
    try {
      clearSessionRefreshBlock()
      const data = await authService.login(payload)
      await fetchProfile()
      return data
    } finally {
      loading.value = false
    }
  }

  async function register(payload: RegisterRequest) {
    loading.value = true
    try {
      clearSessionRefreshBlock()
      const data = await authService.register(payload)
      await fetchProfile()
      return data
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authService.logout()
    } catch {
      // Cookies are cleared server-side when possible; always drop client state.
    }
    authenticated.value = false
    profile.value = null
  }

  async function hydrate(): Promise<boolean> {
    if (authenticated.value && profile.value) return true
    if (hydratePromise) return hydratePromise
    hydratePromise = (async () => {
      try {
        // Probe only: missing cookies must not force-redirect public pages.
        // Protected routes still send guests to login via requireAuth.
        profile.value = await userService.getMe({ skipSessionExpired: true })
        authenticated.value = true
        return true
      } catch {
        authenticated.value = false
        profile.value = null
        return false
      } finally {
        hydratePromise = null
      }
    })()
    return hydratePromise
  }

  function markUnauthenticated() {
    authenticated.value = false
    profile.value = null
  }

  /**
   * Unauthorized / expired session: clear client state, best-effort revoke server
   * cookies, and always send the user to login from wherever they are
   * (except auth screens themselves, to avoid loops on bad credentials).
   */
  async function handleSessionExpired(): Promise<void> {
    if (sessionExpiryPromise) return sessionExpiryPromise

    sessionExpiryPromise = (async () => {
      markUnauthenticated()

      try {
        const { useRealtimeStore } = await import('@/stores/realtime.store')
        useRealtimeStore().reset()
      } catch {
        // Pinia/realtime may be unavailable in unit tests.
      }

      try {
        await authService.logout()
      } catch {
        // Server may already have revoked cookies; client state is cleared above.
      }

      const router = (await import('@/router')).default
      const current = router.currentRoute?.value
      const authScreen =
        current?.name === 'login' ||
        current?.name === 'register' ||
        current?.name === 'password-recovery'
      if (!current || authScreen) return

      const redirect =
        current.fullPath &&
        current.fullPath !== '/' &&
        !String(current.fullPath).startsWith('/auth')
          ? current.fullPath
          : undefined
      await router.replace({
        name: 'login',
        ...(redirect ? { query: { redirect } } : {}),
      })
    })().finally(() => {
      sessionExpiryPromise = null
    })

    return sessionExpiryPromise
  }

  return {
    authenticated,
    profile,
    loading,
    isAuthenticated,
    userId,
    login,
    register,
    fetchProfile,
    logout,
    hydrate,
    markUnauthenticated,
    handleSessionExpired,
  }
})
