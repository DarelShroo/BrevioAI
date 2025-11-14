import { useStoreDeviceType } from '@/modules/brevio/composables/useStoreDeviceType'
import { useStoreNotification } from '@/modules/brevio/composables/useStoreNotification'
import axios from 'axios'
import { h } from 'vue'
import type { RequestHeaders } from './interfaces/request-headers'

export const brevio_api = () => {
  const base_url = import.meta.env.VITE_API_URL

  const get = async (path: string, parameters: { key: string; value: string }[] = []) => {
    try {
      const response = await axios.get(base_url + path, {
        headers: {
          'X-API-KEY': 'AZUCAR',
        },
      })
      return response.data
    } catch (error) {
      console.error('Error en la solicitud GET:', error)
      throw error
    }
  }

  const post = async (
    url: string,
    body: any,
    token: string = '',
    api_key: string = 'AZUCAR',
  ) => {
    try {
      const isFormData = body instanceof FormData

      const requestHeaders: RequestHeaders = {
        headers: {
          'X-API-KEY': api_key,
          'Authorization': `Bearer ${token}`,
        },
      }

      if (!isFormData) {
        requestHeaders.headers['Content-Type'] = 'application/json'
      }

      const endpoint = base_url + url

      const response = await axios.post(endpoint, body, requestHeaders)

      return response
    } catch (error: any) {
      const notification = useStoreNotification()
      const { placement } = useStoreDeviceType()

      const title = error?.response?.data?.message || 'Error en la solicitud'
      const errorMessages: string[] = []

      if (error?.response?.data?.errors) {
        error.response.data.errors.forEach((err: { message: string }) => {
          errorMessages.push(err.message)
        })
      }

      const htmlMessage = errorMessages.join('<br>')

      notification.configNotification(
        'error',
        htmlMessage,
        title,
        placement.value
      )

      return null
    }
  }

  return {
    get,
    post,
  }
}

export const api = brevio_api()
