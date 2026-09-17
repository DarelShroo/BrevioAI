import { beforeEach, describe, expect, it, vi } from 'vitest'
import { http } from '@/services/http'
import * as plansService from '@/services/plans.service'

vi.mock('@/services/http', () => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('plans.service', () => {
  beforeEach(() => {
    vi.mocked(http.get).mockReset()
    vi.mocked(http.post).mockReset()
  })

  it('loads the plans catalog from GET /plans', async () => {
    vi.mocked(http.get).mockResolvedValueOnce({
      data: {
        status: 'success',
        default_plan_id: 'free',
        period_mode: 'calendar_month',
        rolling_days: 30,
        plan_change_usage_policy: 'keep_period_counters',
        checkout_enabled: false,
        billing_provider: null,
        customer_portal_enabled: false,
        plans: [{ plan_id: 'free', name: 'Free' }],
      },
    } as any)

    const result = await plansService.listPlans()
    expect(http.get).toHaveBeenCalledWith('/plans')
    expect(result.default_plan_id).toBe('free')
    expect(result.checkout_enabled).toBe(false)
    expect(result.plans[0].plan_id).toBe('free')
  })

  it('syncs billing state via POST /billing/sync', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: { plan_id: 'pro', synced: true, credits_balance: 4000 },
    } as any)

    const result = await plansService.syncBillingState('cs_test_1')
    expect(http.post).toHaveBeenCalledWith('/billing/sync', { session_id: 'cs_test_1' })
    expect(result.plan_id).toBe('pro')
    expect(result.synced).toBe(true)
  })
})
