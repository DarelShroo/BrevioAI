import { ref, defineComponent } from 'vue'
import { useRoute } from 'vue-router'
import { useStoreDeviceType } from '@/composables/useStoreDeviceType'

export default defineComponent({
  setup() {
    const open = ref<boolean>(false)
    const selectedKeys = ref(['1'])
    const route = useRoute()
    const currentPath = ref<string>(route.path)
    const primaryColor = ref<string>('#1F1A1C')
    const selectedColor = ref<string>('#25282F')
    const { isMobile } = useStoreDeviceType()

    const backgroundColor = ref<{ [key: string]: string }>({
      login: primaryColor.value,
      register: primaryColor.value,
      bravio: primaryColor.value,
    })

    const menuItems = ref([
      { key: 'login', path: '/login', label: 'Login' },
      { key: 'register', path: '/register', label: 'Register' },
      { key: 'bravio', path: '/bravio', label: 'Bravio' },
    ])

    const changeColor = (key: string) => {
      Object.keys(backgroundColor.value).forEach(
        (k) => (backgroundColor.value[k] = primaryColor.value),
      )

      backgroundColor.value[key] = selectedColor.value
    }

    return {
        open,
        selectedKeys,
        currentPath,
        primaryColor,
        selectedColor,
        isMobile,
        menuItems,
        changeColor,
        backgroundColor
    }
  },
})
