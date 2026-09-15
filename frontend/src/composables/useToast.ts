import { useToast as usePrimeToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'

export interface AppToastOptions {
  life?: number
  styleClass?: string
}

export function useAppToast() {
  const toast = usePrimeToast()
  const { t } = useI18n()

  function success(
    detail: string,
    summary = t('toast.success'),
    options: AppToastOptions = {},
  ) {
    toast.add({
      severity: 'success',
      summary,
      detail,
      life: options.life ?? 3500,
      styleClass: options.styleClass,
    })
  }

  function info(
    detail: string,
    summary = t('toast.info'),
    options: AppToastOptions = {},
  ) {
    toast.add({
      severity: 'info',
      summary,
      detail,
      life: options.life ?? 3500,
      styleClass: options.styleClass,
    })
  }

  function warn(
    detail: string,
    summary = t('toast.warning'),
    options: AppToastOptions = {},
  ) {
    toast.add({
      severity: 'warn',
      summary,
      detail,
      life: options.life ?? 4500,
      styleClass: options.styleClass,
    })
  }

  function error(
    detail: string,
    summary = t('toast.error'),
    options: AppToastOptions = {},
  ) {
    toast.add({
      severity: 'error',
      summary,
      detail,
      life: options.life ?? 5500,
      styleClass: options.styleClass,
    })
  }

  return { success, info, warn, error }
}
