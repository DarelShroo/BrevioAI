import { api } from '@/utils/api'
import { Form, message } from 'ant-design-vue'
import { defineComponent, onMounted, reactive, ref, toRaw } from 'vue'
import { useAuthStore } from '../../../../stores/useAuthStore';
import type {
  LanguageTypeResponse,
  ModelTypeResponse,
  SummaryLevelResponse,
  AdvancedContentCombinations,
  CategoryOptions,
  OutputFormatResponse,
} from '../../interfaces/brevio-responses'

const useForm = Form.useForm

export default defineComponent({
  name: 'FormContentComponent',
  props: {
    typeConfiguration: {
      type: String,
    },
    fileList: {
      type: Array as () => { name: string; originFileObj?: File }[],
      default: () => [],
    }
  },
  setup(props, { emit }) {
    const typeConfiguration = ref(props.typeConfiguration)
    const validSourceTypes = ref({
      'summary-youtube': ['video', 'audio'],
      'summary-media': ['video', 'audio'],
      'summary-document': ['text'],
    })

    const authStore = useAuthStore()
    const token = authStore.getToken()

    const validSourceTypesConfiguration = ref(validSourceTypes.value[typeConfiguration.value as keyof typeof validSourceTypes.value] || [])

    const modelRef = reactive({
      language: undefined as string | undefined,
      model: undefined as string | undefined,
      category: undefined as string | undefined,
      style: undefined as string | undefined,
      outputFormat: undefined as string | undefined,
      sourceType: undefined as string | undefined,
      summaryLevel: undefined as string | undefined,
    })

    const rulesRef = reactive({
      language: [{ required: true, message: 'Please select output language' }],
      model: [{ required: true, message: 'Please select LLM model' }],
      category: [{ required: true, message: 'Please select summary category type' }],
      style: [{ required: true, message: 'Please select category style' }],
      outputFormat: [{ required: true, message: 'Please select format type' }],
      sourceType: [],
      summaryLevel: [{ required: true, message: 'Please select summary level' }],
    })

    const languageOptions = ref<LanguageTypeResponse[]>([])
    const modelOptions = ref<ModelTypeResponse[]>([])
    const summaryLevelOptions = ref<SummaryLevelResponse[]>([])

    let advancedContentCombinations: AdvancedContentCombinations = {}

    const categoryOptions = ref<CategoryOptions[]>([])

    const outputFormatOptions = ref<OutputFormatResponse[]>([])

    const fetchLanguagesList = async (): Promise<LanguageTypeResponse[]> => {
      try {
        const response = await api.get('/brevio/languages')
        const languages = response.data?.languages || []
        return Object.entries(languages).map(([, value]) => ({
          value: (value as string).toLowerCase(),
          label:
            (value as string).charAt(0).toUpperCase() + (value as string).toLowerCase().slice(1),
        }))
      } catch (error) {
        console.error('Error fetching languages:', error)
        message.error('Failed to fetch languages')
        return []
      }
    }

    const fetchModelsList = async (): Promise<ModelTypeResponse[]> => {
      try {
        const response = await api.get('/brevio/models')
        const models = response.data?.models || []
        return Object.entries(models).map(([, value]) => ({
          value: (value as string).toLowerCase(),
          label: (value as string).toLowerCase(),
        }))
      } catch (error) {
        console.error('Error fetching models:', error)
        message.error('Failed to fetch models')
        return []
      }
    }

    const fetchOutputFormatsList = async (): Promise<OutputFormatResponse[]> => {
      try {
        const response = await api.get('/brevio/output-formats')
        const outputFormats = response.data?.output_format_types || []
        return Object.entries(outputFormats).map(([, value]) => ({
          value: (value as string).toLowerCase(),
          label: (value as string).toLowerCase(),
        }))
      } catch (error) {
        console.error('Error fetching models:', error)
        message.error('Failed to fetch models')
        return []
      }
    }

    const fetchSummaryLevelsList = async (): Promise<SummaryLevelResponse[]> => {
      try {
        const response = await api.get('/brevio/summary-levels')
        const summaryLevels = response.data?.summary_levels || []
        return Object.entries(summaryLevels).map(([key, value]) => ({
          value: (key as string).toLowerCase(),
          label:
            (key as string).toLowerCase().replace('_', ' ') +
            ' (' +
            (value as string).toLowerCase() +
            ' '.concat('words aproximately per response').toLowerCase() +
            ')',
        }))
      } catch (error) {
        console.error('Error fetching SummaryLevels:', error)
        message.error('Failed to fetch SummaryLevels')
        return []
      }
    }

    const fetchCategoriesStylesList = async (): Promise<AdvancedContentCombinations> => {
      try {
        const response = await api.get('/brevio/categories-styles')
        const advancedContentCombinations = response.data?.advanced_content_combinations || []
        return advancedContentCombinations
      } catch (error) {
        console.error('Error fetching SummaryLevels:', error)
        message.error('Failed to fetch SummaryLevels')
        return {}
      }
    }

    const getStyleOptions = (category: string): { label: string; value: string }[] => {
      const styles = advancedContentCombinations[category];
      if (!styles) return [];

      return styles
        .filter(item => {
          return validSourceTypesConfiguration.value.some(type =>
            item.source_types.includes(type)
          );
        })
        .map(item => {
          return {
            value: item.style,
            label: item.style.charAt(0).toUpperCase() + item.style.slice(1),
          };
        });
    };

    const getSourceTypeOptions = (
      category?: string,
      style?: string,
    ): { label: string; value: string }[] => {
      if (!category || !style) return []

      const categoryItems = advancedContentCombinations[category]
      if (!categoryItems) return []

      const matchedStyle = categoryItems.find((item) => item.style === style)
      if (!matchedStyle) return []

      return matchedStyle.source_types.map((type: string) => ({
        label: type.charAt(0).toUpperCase() + type.slice(1),
        value: type,
      }))
    }

    const onCategoryChange = () => {
      modelRef.style = undefined
      modelRef.sourceType = undefined
    }

    const { resetFields, validate, validateInfos } = useForm(modelRef, rulesRef)

    const fetchBrevio = async () => {
      const formData = new FormData()
      formData.append('language', modelRef.language || '')
      formData.append('model', modelRef.model || '')
      formData.append('category', modelRef.category || '')
      formData.append('style', modelRef.style || '')
      formData.append('format', modelRef.outputFormat || '')
      formData.append('summary_level', modelRef.summaryLevel || '')

      props.fileList.forEach(file => {
        if (file.originFileObj instanceof File) {
          formData.append('files', file.originFileObj)
        }
      })

      console.log('Cuerpo de la solicitud:', formData)

      const response = await api.post('/brevio/summary-documents', formData, token as string)

      if (response) {
        console.log('Respuesta recibida:', response.data)
        return response.data
      }

      console.error('No se pudo obtener respuesta del endpoint brevio/')
      return null
    }



    const onSubmit = () => {
      if(props.fileList.length === 0) {
        message.error('Please upload a file')
        return
      }
      validate()
        .then(() => {
          fetchBrevio()
          message.success('Form submitted successfully')
        })
        .catch((err) => {
          message.error('Please fill all required fields')
        })
    }

    // Fetch data on mount
    onMounted(async () => {
      languageOptions.value = await fetchLanguagesList()
      modelOptions.value = await fetchModelsList()
      summaryLevelOptions.value = await fetchSummaryLevelsList()
      advancedContentCombinations = await fetchCategoriesStylesList()
      categoryOptions.value = Object.keys(advancedContentCombinations).map((key) => ({
        value: key,
        label: key
          .split('_')
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' '),
      }))
      outputFormatOptions.value = await fetchOutputFormatsList()
    })

    return {
      labelCol: { span: 4 },
      wrapperCol: { span: 14 },
      validate,
      validateInfos,
      resetFields,
      modelRef,
      onSubmit,
      languageOptions,
      modelOptions,
      categoryOptions,
      summaryLevelOptions,
      outputFormatOptions,
      getStyleOptions,
      getSourceTypeOptions,
      onCategoryChange,
    }
  },
})
