import { onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth.store'
import { useRealtimeStore } from '@/stores/realtime.store'
import type { SummaryJobEvent } from '@/types/events'
import { jobEventToastClass } from '@/utils/events'

export function useRealtimeNotifications() {
  const auth = useAuthStore()
  const realtime = useRealtimeStore()
  const toast = useAppToast()
  const { t } = useI18n()

  function documentName(event: SummaryJobEvent) {
    return event.document_name?.trim() || t('store.untitled')
  }

  function notify(event: SummaryJobEvent) {
    const name = documentName(event)
    const styleClass = jobEventToastClass(event.job_id)
    const hint = t('notifications.viewSummaryHint')
    
    if (event.type === 'summary.completed') {
      toast.success(
        `${t('notifications.summaryCompletedDetail', { name })} ${hint}`,
        t('notifications.summaryCompleted'),
        { life: 7000, styleClass },
      )
      return
    }

    if (event.type === 'summary.failed') {
      let errorMessage = t('notifications.summaryFailedDetail', { name })

      if (event.error?.code) {
        // En vue-i18n, podemos comprobar si existe la traducción
        const codeKey = `errors.codes.${event.error.code}`
        // Como te() no está destructurado, usamos t() y comparamos
        const translated = t(codeKey)
        if (translated !== codeKey) {
          errorMessage = `${errorMessage} ${translated}`
        } else if (event.error.message && !event.error.message.includes('\n') && !event.error.message.includes('Traceback')) {
          errorMessage = `${errorMessage} ${event.error.message}`
        }
      } else if (event.error?.message && !event.error.message.includes('\n') && !event.error.message.includes('Traceback')) {
        errorMessage = `${errorMessage} ${event.error.message}`
      }

      toast.error(
        `${errorMessage} ${hint}`,
        t('notifications.summaryFailed'),
        { life: 8000, styleClass },
      )
    }
  }

  const stopEvents = realtime.subscribe(notify)

  watch(
    () => auth.isAuthenticated,
    (isAuthenticated) => {
      if (isAuthenticated) {
        realtime.connect()
        return
      }
      realtime.reset()
    },
    { immediate: true },
  )

  onUnmounted(() => {
    stopEvents()
  })

  return { notify }
}
