import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import PlansView from '@/views/PlansView.vue'
import type { PlansCatalog, UserProfile } from '@/types/user'

const listPlansMock = vi.fn()
const fetchProfileMock = vi.fn()
const hydrateMock = vi.fn()

const catalog: PlansCatalog = {
  status: 'success',
  default_plan_id: 'free',
  period_mode: 'calendar_month',
  rolling_days: 30,
  plan_change_usage_policy: 'keep_period_counters',
  checkout_enabled: false,
  billing_provider: null,
  customer_portal_enabled: false,
  show_billing_toggle: true,
  annual_discount_percent: 20,
  sales_email: 'support@brevio.com',
  highlighted_plan_id: 'pro',
  plans: [
    {
      plan_id: 'free',
      name: 'Free',
      version: '1',
      status: 'active',
      documents_per_period: 10,
      pages_per_document: 200,
      pages_per_period: 1000,
      bytes_per_document: 26214400,
      bytes_per_audio: 52428800,
      bytes_per_video: 262144000,
      bytes_per_period: 2621440000,
      credits_per_period: 100,
      rollover_max: 200,
      max_concurrent_jobs: 5,
      scheduler_weight: 1,
      scheduler_priority: 10,
      byok_allowed: true,
      brevio_funded_models: ['qwen3:8b'],
      funds_all_models: false,
      retention_days: 7,
      media_enabled: true,
      youtube_enabled: false,
      price_amount: 0,
      price_currency: 'EUR',
      billing_interval: 'month',
      highlighted: false,
      cta_kind: 'start_free',
      trial_days: null,
    },
    {
      plan_id: 'pro',
      name: 'Pro',
      version: '1',
      status: 'active',
      documents_per_period: 100,
      pages_per_document: 1000,
      pages_per_period: 10000,
      bytes_per_document: 104857600,
      bytes_per_audio: 262144000,
      bytes_per_video: 2147483648,
      bytes_per_period: 214748364800,
      credits_per_period: 4000,
      rollover_max: 8000,
      max_concurrent_jobs: 20,
      scheduler_weight: 5,
      scheduler_priority: 50,
      byok_allowed: true,
      brevio_funded_models: ['qwen3:8b', 'gpt-4o-mini'],
      funds_all_models: false,
      retention_days: 30,
      media_enabled: true,
      youtube_enabled: true,
      price_amount: 9.99,
      price_currency: 'EUR',
      billing_interval: 'month',
      highlighted: true,
      cta_kind: 'choose_pro',
      trial_days: null,
      annual_price_amount: 95.9,
    },
    {
      plan_id: 'business',
      name: 'Business',
      version: '1',
      status: 'active',
      documents_per_period: 500,
      pages_per_document: 5000,
      pages_per_period: 50000,
      bytes_per_document: 524288000,
      bytes_per_audio: 1073741824,
      bytes_per_video: 10737418240,
      bytes_per_period: 5368709120000,
      credits_per_period: 20000,
      rollover_max: 40000,
      max_concurrent_jobs: 50,
      scheduler_weight: 20,
      scheduler_priority: 100,
      byok_allowed: true,
      brevio_funded_models: [],
      funds_all_models: true,
      retention_days: 90,
      media_enabled: true,
      youtube_enabled: true,
      price_amount: 19.99,
      price_currency: 'EUR',
      billing_interval: 'month',
      highlighted: false,
      cta_kind: 'contact_sales',
      trial_days: null,
      annual_price_amount: 191.9,
    },
  ],
}

const profile: UserProfile = {
  id: 'u1',
  username: 'testuser',
  email: 'test@example.com',
  user_credit: 40,
  plan_id: 'free',
  plan_name: 'Free',
  plan_version: '1',
  entitlements: {
    plan_id: 'free',
    plan_name: 'Free',
    plan_version: '1',
    period_start: '2026-09-01T00:00:00+00:00',
    period_end: '2026-10-01T00:00:00+00:00',
    period_mode: 'calendar_month',
    limits: {
      documents_per_period: 10,
      pages_per_document: 200,
      pages_per_period: 1000,
      bytes_per_document: 26214400,
      bytes_per_period: 2621440000,
      credits_per_period: 100,
      max_concurrent_jobs: 5,
      media_enabled: true,
      youtube_enabled: false,
      byok_allowed: true,
    },
    usage: {
      documents_used: 2,
      pages_used: 10,
      bytes_used: 1000,
      credits_used: 10,
      concurrent_jobs: 0,
    },
    remaining: {
      documents: 8,
      pages: 190,
      bytes: 52427800,
      credits: 40,
      concurrent_jobs: 1,
    },
  },
}

const authState = {
  profile: profile as UserProfile | null,
  isAuthenticated: true,
  fetchProfile: fetchProfileMock,
  hydrate: hydrateMock,
}

vi.mock('@/services/plans.service', () => ({
  listPlans: (...args: unknown[]) => listPlansMock(...args),
}))

vi.mock('@/stores/auth.store', () => ({
  useAuthStore: () => authState,
}))

const stubs = {
  StateBlock: {
    props: ['loading', 'error'],
    emits: ['retry'],
    template:
      '<div><div v-if="loading" data-testid="state-loading" /><div v-else-if="error" data-testid="state-error">{{ error }}</div><slot v-else /></div>',
  },
  Button: {
    template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>',
    props: ['label', 'disabled', 'severity', 'outlined'],
  },
  Accordion: { template: '<div class="acc"><slot /></div>' },
  AccordionPanel: { template: '<div><slot /></div>' },
  AccordionHeader: { template: '<div><slot /></div>' },
  AccordionContent: { template: '<div><slot /></div>' },
}

describe('PlansView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    listPlansMock.mockReset()
    fetchProfileMock.mockReset()
    hydrateMock.mockReset()
    authState.profile = profile
    authState.isAuthenticated = true
    listPlansMock.mockResolvedValue(catalog)
    fetchProfileMock.mockResolvedValue(profile)
    hydrateMock.mockResolvedValue(true)
  })

  async function mountView() {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/plans', name: 'plans', component: PlansView },
        { path: '/profile', name: 'profile', component: { template: '<div />' } },
        { path: '/auth/login', name: 'login', component: { template: '<div />' } },
        { path: '/auth/register', name: 'register', component: { template: '<div />' } },
      ],
    })
    await router.push('/plans')
    await router.isReady()
    const wrapper = mount(PlansView, {
      global: {
        plugins: [router],
        stubs,
        directives: { tooltip: () => {} },
      },
    })
    await flushPromises()
    return wrapper
  }

  it('renders priced tiers with Pro highlighted', async () => {
    const wrapper = await mountView()
    expect(wrapper.get('[data-testid="plan-card-free"]').text()).toContain('Free')
    expect(wrapper.get('[data-testid="plan-card-pro"]').text()).toContain('Pro')
    expect(wrapper.get('[data-testid="plan-card-business"]').text()).toContain('Business')
    expect(wrapper.get('[data-testid="plan-popular-badge"]').text().length).toBeGreaterThan(0)
    expect(wrapper.get('[data-testid="plans-current"]').text()).toContain('Free')
    expect(wrapper.get('[data-testid="plan-cta-current"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-testid="plans-billing-toggle"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="plan-card-pro"]').text()).toMatch(/9[,.]99|€/)
    expect(wrapper.get('[data-testid="plan-card-free"]').text()).toMatch(/rollover|acumulaci|créditos|credits/i)
    expect(wrapper.get('[data-testid="plan-card-pro"]').text()).toMatch(/1000|1[,.]000/)
  })

  it('lets guests browse the catalog without current-plan panel', async () => {
    authState.isAuthenticated = false
    authState.profile = null
    hydrateMock.mockResolvedValue(false)
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="plans-guest-notice"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="plans-current"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="plan-card-free"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-testid="plan-cta-register"]').length).toBeGreaterThan(0)
    expect(fetchProfileMock).not.toHaveBeenCalled()
  })

  it('shows error when catalog fetch fails', async () => {
    listPlansMock.mockRejectedValueOnce(new Error('network down'))
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/plans', name: 'plans', component: PlansView }],
    })
    await router.push('/plans')
    await router.isReady()
    const wrapper = mount(PlansView, {
      global: {
        plugins: [router],
        stubs,
        directives: { tooltip: () => {} },
      },
    })
    await flushPromises()
    expect(wrapper.get('[data-testid="state-error"]').text()).toMatch(/network|down|error/i)
  })
})
