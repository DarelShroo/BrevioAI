import { defineComponent, ref, computed } from 'vue'
import { notification } from 'ant-design-vue'
import { useMenuBravioStore } from '@/stores/useMenuBravioStore'
import { useStoreDeviceType } from '@/composables/useStoreDeviceType'
import { languageMessages } from '@/constants/languageMessages.constants'
import { modelMessages } from '@/constants/modelMessages.constants'

export default defineComponent({
  setup() {
    const languageOptions = ref([
      { value: 'ES', label: 'ES' },
      { value: 'RU', label: 'RU' },
      { value: 'CU', label: 'CU' },
    ])

    const modelOptions = ref([
      { value: 'gpt-4', label: 'gpt-4' },
      { value: 'gpt-o-4', label: 'gpt-0-4' },
      { value: 'gpt-3', label: 'gpt-3' },
    ])

    const selectedModel = ref<string | undefined>(undefined)
    const selectedLanguage = ref<string | undefined>(undefined)

    const menuBravioStore = useMenuBravioStore()
    const { isMobile } = useStoreDeviceType()

    const openNotificationWithIcon = (select: 'language' | 'model') => {
      if (select === 'language' && selectedLanguage.value) {
        const { languageSelectedMessage } = languageMessages(selectedLanguage.value)
        notification['info']({
          message: 'Language',
          description: languageSelectedMessage.value,
          placement: placement.value,
        })
      } else if (select === 'model' && selectedModel.value) {
        const { modelSelectedMessage } = modelMessages(selectedModel.value)
        notification['info']({
          message: 'GPT Model',
          description: modelSelectedMessage.value,
          placement: placement.value,
        })
      }
    }

    const placement = computed(() => {
      return isMobile ? 'bottom' : 'topRight'
    })

    const filterOption = (input: string, option: any) => {
      return option.value.toLowerCase().indexOf(input.toLowerCase()) >= 0
    }

    const { placeHolderSelectedModel } = modelMessages()
    const {placeHolderSelectedLanguage} = languageMessages()

    return {
      modelOptions,
      languageOptions,
      menuBravioStore,
      selectedModel,
      selectedLanguage,
      openNotificationWithIcon,
      filterOption,
      placeHolderSelectedModel,
      placeHolderSelectedLanguage
    }
  },
})
