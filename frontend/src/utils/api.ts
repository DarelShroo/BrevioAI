import axios from 'axios'
import type { BrevioRequest } from '@/modules/ConfigBrevio/interfaces/brevio-request'
import { LanguageType } from '@/modules/ConfigBrevio/enums/language.enum'
import { useStoreNotification } from '@/modules/ConfigBrevio/composables/useStoreNotification'
import { useStoreDeviceType } from '@/modules/ConfigBrevio/composables/useStoreDeviceType'

export const api = () => {
  const get = async (path: string, parameters: { key: string; value: string }[] = []) => {
    try {
      const response = await axios.get(path)
      return response.data
    } catch (error) {
      console.error('Error en la solicitud GET:', error)
      throw error
    }
  }

  const post = async (
    path: string,
    body: BrevioRequest = { url: '', language: LanguageType.SPANISH },
    token: string | null = null,
  ) => {
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {}
      const response = await axios.post(path, body, { headers })

      if (response.status !== 200) {
        throw new Error(`La solicitud POST falló con el estado: ${response.status}`)
      }
      console.log(response.data)
      return response.data
    } catch (error: any) {
      const notification = useStoreNotification()
      const { placement } = useStoreDeviceType()
      notification.configNotification(
        'error',
        error.response.data.detail.error_message,
        error.status,
        placement.value,
      )
    }
  }

  return {
    get,
    post,
  }
}
