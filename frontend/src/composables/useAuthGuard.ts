import { useAuthStore } from '@/stores/useAuthStore'
import { useRouter } from 'vue-router'

export function useAuthGuard() {
  const auth = useAuthStore()
  const router = useRouter()

  if (!auth.userLoggedIn) {
    router.push({ name: '/' }) // o donde quieras redirigir
  }
}
