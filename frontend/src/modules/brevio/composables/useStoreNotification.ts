import { notification, type NotificationPlacement } from 'ant-design-vue'
import { h } from 'vue'

export const useStoreNotification = () => {
  const configNotification = (
    typeNotification: 'success' | 'info' | 'warning' | 'error' = 'info',
    description: string,
    message: string,
    placement: NotificationPlacement
  ) => {
    notification[typeNotification]({
      message,
      description: () => h('div', { innerHTML: description }), 
      placement,
    })
  }

  return {
    configNotification,
  }
}
