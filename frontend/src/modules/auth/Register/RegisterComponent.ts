import { computed, defineComponent, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { api } from '@/utils/api'
import { useRouter } from 'vue-router'
import type { RegisterRequest } from './interfaces/register-request'
import { useAuthStore } from '@/stores/useAuthStore'

export default defineComponent({
  name: 'RegisterView',
  setup() {
    const router = useRouter()
    const formRef = ref()
    const loading = ref(false)
    const auth = useAuthStore()


    const formState = reactive({
      username: '',
      email: '',
      password: '',
    })

    const usernameRegex = /^[a-zA-Z0-9_.-]{6,10}$/
    const passwordRegex = /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_])[A-Za-z\d\W_]{8,}$/
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    const rules = {
      username: [
        { required: true, message: 'El nombre de usuario es obligatorio' },
        {
          validator: (_rule: any, value: string) => {
            if (!value || usernameRegex.test(value)) {
              return Promise.resolve()
            }
            return Promise.reject(
              'Debe tener entre 6 y 10 caracteres y solo usar letras, números, guiones, puntos o guiones bajos',
            )
          },
          trigger: 'change',
        },
      ],
      email: [
        { required: true, message: 'El email es obligatorio' },
        {
          validator: (_rule: any, value: string) => {
            if (!value || emailRegex.test(value)) {
              return Promise.resolve()
            }
            return Promise.reject(
              'Debe ser un formato de email valido',
            )
          },
          trigger: 'change',
        },
      ],
      password: [
        { required: true, message: 'La contraseña es obligatoria' },
        {
          validator: (_rule: any, value: string) => {
            if (!value || passwordRegex.test(value)) {
              return Promise.resolve()
            }
            return Promise.reject(
              'La contraseña debe tener almenos 8 caracteres, una letra mayúscula, una letra minúscula, un número y un carácter especial',
            )
          },
          trigger: 'change',
        },
      ],
    }

    const isDisabled = computed(() => {
      return !formState.username || !formState.email || !formState.password || loading.value
    })

    const register = async (registerRequest: RegisterRequest) => {
      loading.value = true
      try {
        const response = await api.post('/auth/register', registerRequest)
        if (response?.status === 201) {
          console.log(response.data)
          auth.setToken(response.data.data.access_token)
          message.success(`Bienvenido, ${formState.username}`)
          router.push({ name: 'brevio' })
        }
      } catch { 
        message.error('Error al iniciar sesión. Verifica tus credenciales.')
      } finally {
        loading.value = false
      }
    }

    // Handle form submission
    const handleRegister = () => {
      formRef.value
        .validateFields()
        .then(() => {
          const { username, email, password } = formState
          register({ username, email, password })
        })
        .catch((error: any) => {
          console.log('Form validation failed:', error)
        })
    }

    onMounted(() => {
      formRef.value.validateFields(['username','email', 'password'], { force: true }).catch(() => {})
    })

    return {
      formRef,
      formState,
      handleRegister,
      isDisabled,
      loading,
      rules,
    }
  },
})
