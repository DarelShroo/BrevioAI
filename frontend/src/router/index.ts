import LoginView from '@/modules/auth/Login/LoginView.vue'
import RegisterView from '@/modules/auth/Register/RegisterView.vue'
import HomeView from '@/modules/content/components/Home/HomeView.vue'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/auth',
      children: [
        {
          path: 'login',
          name: 'login',
          component: LoginView,
        },
        {
          path: 'register',
          name: 'register',
          component: RegisterView,
        },
      ],
    },
    {
      path: '/brevio',
      name: 'brevio',
      component: HomeView,
    },
  ],
})

export default router
