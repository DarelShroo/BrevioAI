import { createRouter, createWebHistory } from 'vue-router'
import { requireAuth, requireGuest } from '@/router/guards'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/summary',
    },
    {
      path: '/auth',
      component: () => import('@/layouts/AuthLayout.vue'),
      children: [
        {
          path: 'login',
          name: 'login',
          component: () => import('@/views/auth/LoginView.vue'),
          beforeEnter: requireGuest,
        },
        {
          path: 'register',
          name: 'register',
          component: () => import('@/views/auth/RegisterView.vue'),
          beforeEnter: requireGuest,
        },
        {
          path: 'password-recovery',
          name: 'password-recovery',
          component: () => import('@/views/auth/PasswordRecoveryView.vue'),
        },
      ],
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      beforeEnter: requireAuth,
      children: [
        {
          path: 'summary',
          name: 'summary',
          component: () => import('@/views/SummaryView.vue'),
        },
        {
          path: 'store',
          name: 'store',
          component: () => import('@/views/StoreView.vue'),
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/ProfileView.vue'),
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/summary',
    },
  ],
})

export default router
