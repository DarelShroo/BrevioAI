import { defineComponent, onBeforeMount, ref } from 'vue';
import { useMenuBravioStore } from '../../stores/useMenuBravioStore';
import { modelMessages } from '../../constants/model-messages.constants';
import { languageMessages } from '../../constants/language-messages.constants';
import { api } from '@/utils/api';
import type { LanguageTypeResponse } from '../../interfaces/language-response';
import type { ModelTypeResponse } from '../../interfaces/model-response';
import { useStoreDeviceType } from '../../composables/useStoreDeviceType';
import { useStoreNotification } from '../../composables/useStoreNotification';

export default defineComponent({
  async setup() {
    const languageOptions = ref<LanguageTypeResponse[]>([]);
    const modelOptions = ref<ModelTypeResponse[]>([]);

    const fetchLanguagesList = async (): Promise<LanguageTypeResponse[]> => {
      try {
        const response = await api().get('http://localhost:8000/languages');
        const languages = typeof response === 'string' ? JSON.parse(response) : response;
        const LanguageEnum = Object.freeze(languages);
        const languages_obj = Object.entries(LanguageEnum).map(([key, value]) => ({
          value: key,
          label: value as string,
        }));
        return languages_obj;
      } catch (error) {
        console.error('Error fetching languages:', error);
        return [];
      }
    };

    const fetchModelsList = async (): Promise<ModelTypeResponse[]> => {
      try {
        const response = await api().get('http://localhost:8000/models');
        const models = typeof response === 'string' ? JSON.parse(response) : response;
        const ModelsEnum = Object.freeze(models);
        const models_obj = Object.entries(ModelsEnum).map(([key, value]) => ({
          value: key,
          label: value as string,
        }));
        return models_obj;
      } catch (error) {
        console.error('Error fetching models:', error);
        return [];
      }
    };

    onBeforeMount(async () => {
      languageOptions.value = await fetchLanguagesList();
      modelOptions.value = await fetchModelsList();
    });

    const selectedModel = ref<string | undefined>(undefined);
    const selectedLanguage = ref<string | undefined>(undefined);
    const  {placement} = useStoreDeviceType()
    const menuBravioStore = useMenuBravioStore()
    const {configNotification} = useStoreNotification()
    const configNotificationReactive = ref(configNotification)

    const openNotificationWithIcon = (select: 'language' | 'model') => {
      const message = select.charAt(0).toUpperCase() + select.slice(1)
      if (select === 'language' && selectedLanguage.value) {
        const { languageSelectedMessage } = languageMessages(selectedLanguage.value)
        configNotificationReactive.value('info', languageSelectedMessage.value, message, placement.value)
      } else if (select === 'model' && selectedModel.value) {
        const { modelSelectedMessage } = modelMessages(selectedModel.value)
        configNotificationReactive.value('info', modelSelectedMessage.value, message, placement.value)
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
