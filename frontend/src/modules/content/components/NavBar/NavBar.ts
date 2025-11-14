import { computed, defineComponent, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStoreDeviceType } from '../../../brevio/composables/useStoreDeviceType'
import { useAuthStore } from '@/stores/useAuthStore'

export default defineComponent({
  name: 'NavBar',
  setup() {
    const open = ref<boolean>(false)
    const selectedKeys = ref(['1'])
    const route = useRoute()
    const currentPath = computed(() => route.path)
    const primaryColor = ref<string>('#1F1A1C')
    const selectedColor = ref<string>('#25282F')
    const { isMobile } = useStoreDeviceType()
    const auth = useAuthStore()
    const isAuthenticated = computed(() => auth.userLoggedIn)

    const backgroundColor = ref<{ [key: string]: string }>({
      login: primaryColor.value,
      register: primaryColor.value,
      brevio: primaryColor.value,
      logout: primaryColor.value,
      profile: primaryColor.value
    })

    const menuItems = computed(() =>
      [
        { key: 'login', path: '/auth/login', label: 'Login', visible: !isAuthenticated.value },
        { key: 'register', path: '/auth/register', label: 'Register', visible: !isAuthenticated.value },
        { key: 'brevio', path: '/brevio', label: 'Create', visible: isAuthenticated.value },
        { key: 'profile', path: '/profile', label: 'Profile', visible: isAuthenticated.value },
        { key: 'logout', path: '/', label: 'Logout', visible: isAuthenticated.value },
      ].filter(item => item.visible)
    )

    const router = useRouter()

    const handleClick = (item: any) => {
      changeColor(item.key)
      goTo(item.path)
    }

    const changeColor = (key: string) => {
      Object.keys(backgroundColor.value).forEach(
        (k) => (backgroundColor.value[k] = primaryColor.value),
      )
      backgroundColor.value[key] = selectedColor.value
    }

    const goTo = (path: string) => {
      router.push(path)
      console.log('goto', path)
    }

    const goHome = () => {
      router.push('/')
    }

    const cancel = () => {
      console.log('cancel logout')
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
      backgroundColor,
      goTo,
      handleClick,
      logout: auth.logout,
      cancel,
      goHome
    }
  },
})
