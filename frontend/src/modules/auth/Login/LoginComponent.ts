import { computed, defineComponent, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { api } from '@/utils/api'
import { useRouter } from 'vue-router'
import type { LoginRequest } from './interfaces/login-request'
import {useAuthStore} from '@/stores/useAuthStore'
export default defineComponent({
  name: 'LoginView',
  setup() {
    const router = useRouter()
    const formRef = ref()
    const loading = ref(false)
    const auth = useAuthStore()

    const formState = reactive({
      identity: '',
      password: ''
    })

    const rules = {
      identity: [
        { required: true, message: 'Por favor, ingresa tu usuario o email' }
      ],
      password: [
        { required: true, message: 'Por favor, ingresa tu contraseña' }
      ]
    }

    const isDisabled = computed(() => {
      return !formState.identity || !formState.password || loading.value
    })

    const login = async (loginRequest: LoginRequest) => {
      loading.value = true
      try {
        const response = await api.post('/auth/login', loginRequest)
        if (response?.status === 200) {
          auth.setToken(response.data.data.access_token)
          message.success(`Bienvenido, ${formState.identity}`)
          router.push({ name: 'brevio' })
        }
      } catch (error) {
        message.error('Error al iniciar sesión. Verifica tus credenciales.')
      } finally {
        loading.value = false
      }
    }

    // Handle form submission
    const handleLogin = () => {
      formRef.value
        .validateFields()
        .then(() => {
          const { identity, password } = formState
          login({ identity, password })
        })
        .catch((error: any) => {
          console.log('Form validation failed:', error)
        })
    }

    onMounted(() => {
      formRef.value.validateFields(['identity', 'password'], { force: true }).catch(() => {})
    })

    return {
      formRef,
      formState,
      handleLogin,
      isDisabled,
      loading,
      rules
    }
  }
})
