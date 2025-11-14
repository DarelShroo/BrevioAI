import LoginView from '@/modules/auth/Login/LoginView.vue'
import RegisterView from '@/modules/auth/Register/RegisterView.vue'
import ContentBrevio from '@/modules/brevio/components/ContentBrevio/ContentBrevioView.vue'
import { defineComponent } from 'vue'

import { useRoute } from 'vue-router'
export default defineComponent({
  name: 'ContentHome',
  components: {
    ContentBrevio,
    LoginView,
    RegisterView,
  },
  setup() {
    const route = useRoute()

    return {
      route,
    }
  },
})
