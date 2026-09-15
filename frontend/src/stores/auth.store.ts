import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authService from '@/services/auth.service'
import type { LoginRequest, RegisterRequest } from '@/types/auth'
import type { UserProfile } from '@/types/user'
import * as userService from '@/services/user.service'

export const useAuthStore = defineStore('auth', () => {
  const authenticated = ref(false)
  const profile = ref<UserProfile | null>(null)
  const loading = ref(false)
  let hydratePromise: Promise<boolean> | null = null

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
        await fetchProfile()
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
  }
})
