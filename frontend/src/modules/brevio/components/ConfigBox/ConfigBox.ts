import { api } from '@/utils/api'
import { defineComponent, onBeforeMount, ref } from 'vue'
import { useMenuBravioStore } from '../../../../stores/useMenuBravioStore'
import { useStoreDeviceType } from '../../composables/useStoreDeviceType'
import { useStoreNotification } from '../../composables/useStoreNotification'
import { languageMessages } from '../../constants/language-messages.constants'
import { modelMessages } from '../../constants/model-messages.constants'
import type { ModelTypeResponse } from '../../interfaces/brevio-responses'
import type { LanguageTypeResponse } from '../../interfaces/language-response'

export default defineComponent({
  async setup() {
    const languageOptions = ref<LanguageTypeResponse[]>([])
    const modelOptions = ref<ModelTypeResponse[]>([])

    const fetchLanguagesList = async (): Promise<LanguageTypeResponse[]> => {
      try {
        const response = await api.get('/brevio/languages')
        const languages =
          typeof response === 'string' ? JSON.parse(response) : response.data.languages
        const LanguageEnum = Object.freeze(languages)
        const languages_obj = Object.entries(LanguageEnum).map(([, value]) => ({
          value: (value as string).toLowerCase(),
          label: (value as string).toLowerCase(),
        }))

        return languages_obj
      } catch (error) {
        console.error('Error fetching languages:', error)
        return []
      }
    }

    const fetchModelsList = async (): Promise<ModelTypeResponse[]> => {
      try {
        const response = await api.get('/brevio/models')
        const models = typeof response === 'string' ? JSON.parse(response) : response.data.models
        const ModelsEnum = Object.freeze(models)
        const models_obj = Object.entries(ModelsEnum).map(([, value]) => ({
          value: (value as string).toLowerCase(),
          label: (value as string).toLowerCase(),
        }))
        return models_obj
      } catch (error) {
        console.error('Error fetching models:', error)
        return []
      }
    }

    onBeforeMount(async () => {
      languageOptions.value = await fetchLanguagesList()
      modelOptions.value = await fetchModelsList()
    })

    const selectedModel = ref<string | undefined>(undefined)
    const selectedLanguage = ref<string | undefined>(undefined)
    const { placement } = useStoreDeviceType()
    const menuBravioStore = useMenuBravioStore()
    const { configNotification } = useStoreNotification()
    const configNotificationReactive = ref(configNotification)

    const openNotificationWithIcon = (select: 'language' | 'model') => {
      const message = select.charAt(0).toUpperCase() + select.slice(1)
      if (select === 'language' && selectedLanguage.value) {
        console.log(selectedLanguage)
        const { languageSelectedMessage } = languageMessages(selectedLanguage.value)
        configNotificationReactive.value(
          'info',
          languageSelectedMessage.value,
          message,
          placement.value,
        )
      } else if (select === 'model' && selectedModel.value) {
        const { modelSelectedMessage } = modelMessages(selectedModel.value)
        configNotificationReactive.value(
          'info',
          modelSelectedMessage.value,
          message,
          placement.value,
        )
      }
    }

    const filterOption = (input: string, option: any) => {
      return option.value.toLowerCase().indexOf(input.toLowerCase()) >= 0
    }

    const { placeHolderSelectedModel } = modelMessages()
    const { placeHolderSelectedLanguage } = languageMessages()

    return {
      modelOptions,
      languageOptions,
      menuBravioStore,
      selectedModel,
      selectedLanguage,
      openNotificationWithIcon,
      filterOption,
      placeHolderSelectedModel,
      placeHolderSelectedLanguage,
    }
  },
})
