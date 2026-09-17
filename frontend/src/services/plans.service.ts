import { http } from '@/services/http'
import type { PlansCatalog } from '@/types/user'

export async function listPlans(): Promise<PlansCatalog> {
  const { data } = await http.get<PlansCatalog>('/plans')
  return data
}

export async function createCheckoutSession(
  planId: string,
  billingCycle: 'month' | 'year',
  successUrl: string,
  cancelUrl: string
): Promise<{ url: string }> {
  const { data } = await http.post<{ url: string }>('/billing/checkout', {
    plan_id: planId,
    billing_cycle: billingCycle,
    success_url: successUrl,
    cancel_url: cancelUrl
  })
  return data
}

export async function createPortalSession(returnUrl: string): Promise<{ url: string }> {
  const { data } = await http.post<{ url: string }>('/billing/portal', {
    return_url: returnUrl
  })
  return data
}

export interface BillingSyncResult {
  plan_id: string
  plan_version?: string | null
  stripe_subscription_status?: string | null
  credits_balance?: number
  credits_granted?: boolean
  synced: boolean
  reason?: string
  price_id?: string
  status?: string
}

/** After Stripe Checkout return: pull plan + credits from Stripe into the account. */
export async function syncBillingState(sessionId?: string): Promise<BillingSyncResult> {
  const { data } = await http.post<BillingSyncResult>('/billing/sync', {
    session_id: sessionId || null,
  })
  return data
}
