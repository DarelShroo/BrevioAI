import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import UserMenu from '@/components/layout/UserMenu.vue'

describe('UserMenu', () => {
  it('opens a menu with a profile link and logout action', async () => {
    setActivePinia(createPinia())
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'home', component: { template: '<div />' } },
        { path: '/profile', name: 'profile', component: { template: '<div />' } },
      ],
    })
    await router.push('/')
    await router.isReady()

    const wrapper = mount(UserMenu, {
      global: {
        plugins: [router],
      },
    })

    await wrapper.get('[data-testid="user-menu"]').trigger('click')
    const profile = wrapper.get('[data-testid="user-menu-profile"]')
    expect(profile.element.tagName).toBe('A')
    expect(profile.attributes('href')).toContain('/profile')
    expect(wrapper.get('[role="menuitem"].danger').element.tagName).toBe('BUTTON')
  })
})
