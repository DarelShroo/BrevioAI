import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'

export async function requireAuth(
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext,
) {
  const auth = useAuthStore()
  const ok = await auth.hydrate()
  if (!ok) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }
  next()
}

export async function requireGuest(
  _to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext,
) {
  const auth = useAuthStore()
  const ok = await auth.hydrate()
  if (ok) {
    next({ name: 'summary' })
    return
  }
  next()
}
