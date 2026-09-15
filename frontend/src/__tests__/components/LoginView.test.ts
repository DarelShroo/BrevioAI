import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import LoginView from '@/views/auth/LoginView.vue'

const loginMock = vi.fn()

vi.mock('@/stores/auth.store', () => ({
  useAuthStore: () => ({
    loading: false,
    login: loginMock,
  }),
}))

describe('LoginView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    loginMock.mockReset()
  })

  async function mountLogin() {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/login', name: 'login', component: LoginView },
        { path: '/summary', name: 'summary', component: { template: '<div />' } },
        { path: '/auth/register', name: 'register', component: { template: '<div />' } },
        {
          path: '/auth/password-recovery',
          name: 'password-recovery',
          component: { template: '<div />' },
        },
      ],
    })
    await router.push('/auth/login')
    await router.isReady()

    return mount(LoginView, {
      global: {
        plugins: [router],
        stubs: {
          Button: {
            template: '<button type="submit" :disabled="disabled"><slot />{{ label }}</button>',
            props: ['label', 'loading', 'disabled'],
          },
          InputText: {
            template:
              '<input :id="id" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
            props: ['id', 'modelValue', 'invalid'],
          },
          Password: {
            template:
              '<input :id="inputId" type="password" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
            props: ['inputId', 'modelValue', 'invalid', 'feedback', 'toggleMask', 'inputClass'],
          },
          Message: { template: '<div class="message"><slot /></div>' },
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })
  }

  it('shows validation errors for empty submit', async () => {
    const wrapper = await mountLogin()
    // Form submit still validates even when the button would be disabled in the UI.
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(wrapper.text()).toMatch(/Identity is required/i)
    expect(wrapper.text()).toMatch(/Password is required/i)
    expect(loginMock).not.toHaveBeenCalled()
  })

  it('submits login credentials', async () => {
    loginMock.mockResolvedValueOnce({})
    const wrapper = await mountLogin()
    await wrapper.find('#login-identity').setValue('tester1')
    await wrapper.find('#login-password').setValue('Aa1@aaaa')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(loginMock).toHaveBeenCalledWith({
      identity: 'tester1',
      password: 'Aa1@aaaa',
    })
  })

  it('renders welcome copy and auth links', async () => {
    const wrapper = await mountLogin()
    expect(wrapper.text()).toContain('Welcome back')
    expect(wrapper.text()).toContain('Sign in with your username or email.')
    expect(wrapper.text()).toContain('Create account')
    expect(wrapper.text()).toContain('Forgot password?')
    expect(wrapper.text()).toContain('Sign in')
  })
})
