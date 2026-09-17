import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import AppSidebar from '@/components/layout/AppSidebar.vue'

describe('AppSidebar', () => {
  async function mountSidebar() {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/summary', name: 'summary', component: { template: '<div />' } },
        { path: '/store', name: 'store', component: { template: '<div />' } },
        { path: '/plans', name: 'plans', component: { template: '<div />' } },
        { path: '/profile', name: 'profile', component: { template: '<div />' } },
        { path: '/comparar', name: 'comparar', component: { template: '<div />' } },
        { path: '/comparar/:slug', name: 'comparar-slug', component: { template: '<div />' } },
      ],
    })
    await router.push('/summary')
    await router.isReady()

    return mount(AppSidebar, {
      global: {
        plugins: [router],
        stubs: {
          AppLogo: { template: '<div class="logo-stub" />' },
        },
      },
    })
  }

  it('exposes primary destinations as links', async () => {
    const wrapper = await mountSidebar()
    const store = wrapper.get('[data-testid="nav-store"]')
    expect(store.element.tagName).toBe('A')
    expect(store.attributes('href')).toContain('/store')
    expect(wrapper.get('[data-testid="nav-plans"]').attributes('href')).toContain('/plans')
    expect(wrapper.get('[data-testid="nav-logout"]').element.tagName).toBe('BUTTON')
  })
})
