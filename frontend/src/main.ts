import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import { definePreset } from '@primevue/themes'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import '@/assets/styles/main.css'

const BrevioPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#eefbf9',
      100: '#d8f6f2',
      200: '#b3ebe4',
      300: '#7fdad0',
      400: '#45c7ba',
      500: '#1fb8a8',
      600: '#149688',
      700: '#12786e',
      800: '#135f58',
      900: '#144e49',
      950: '#052f2d',
    },
  },
})

const app = createApp(App)

app.use(createPinia())
app.use(i18n)
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: BrevioPreset,
    options: {
      darkModeSelector: false,
      cssLayer: false,
    },
  },
})
app.use(ToastService)
app.use(ConfirmationService)
app.directive('tooltip', Tooltip)

app.mount('#app')
