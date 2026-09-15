import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import AuthLayout from '@/layouts/AuthLayout.vue'

describe('AuthLayout', () => {
  async function mountLayout() {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { template: '<div />' } }],
    })
    await router.push('/')
    await router.isReady()

    return mount(AuthLayout, {
      global: {
        plugins: [router],
        stubs: {
          RouterView: { template: '<div class="router-view-stub">form</div>' },
          AuthHeroPanel: {
            template:
              '<aside class="auth-hero"><h1>Summaries that stay faithful to the source.</h1><p>Upload documents, media, or YouTube playlists.</p></aside>',
          },
          LanguageSwitcher: { template: '<div data-testid="locale-select" />' },
        },
      },
    })
  }

  it('renders split hero copy and auth card', async () => {
    const wrapper = await mountLayout()
    expect(wrapper.text()).toContain('Summaries that stay faithful to the source.')
    expect(wrapper.text()).toContain('Upload documents, media, or YouTube playlists.')
    expect(wrapper.find('.auth-hero').exists()).toBe(true)
    expect(wrapper.find('.auth-panel').exists()).toBe(true)
    expect(wrapper.find('.router-view-stub').exists()).toBe(true)
  })
})
