<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  Check,
  ChevronDown,
  HelpCircle,
  KeyRound,
  Minus,
} from '@lucide/vue'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import Button from 'primevue/button'
import StateBlock from '@/components/common/StateBlock.vue'
import * as plansService from '@/services/plans.service'
import { useAuthStore } from '@/stores/auth.store'
import type { PlanCatalogItem, PlansCatalog } from '@/types/user'
import { parseApiError } from '@/utils/errors'
import { formatByteSize, formatPeriodDate, formatPlanNumber } from '@/utils/plans'

type BillingCycle = 'month' | 'year'

const { t, locale } = useI18n()
const auth = useAuthStore()
const router = useRouter()

const loading = ref(false)
const error = ref<string | null>(null)
const catalog = ref<PlansCatalog | null>(null)
const billingCycle = ref<BillingCycle>('month')
const compareOpen = ref(false)

const isAuthenticated = computed(() => auth.isAuthenticated)
const currentPlanId = computed(
  () => auth.profile?.plan_id || auth.profile?.entitlements?.plan_id || '',
)
const entitlements = computed(() =>
  isAuthenticated.value ? auth.profile?.entitlements || null : null,
)
const plans = computed(() =>
  (catalog.value?.plans || []).filter((p) => p.status === 'active'),
)
const showBillingToggle = computed(
  () =>
    Boolean(catalog.value?.show_billing_toggle) &&
    plans.value.some((p) => p.annual_price_amount != null),
)
const annualDiscount = computed(() => {
  let maxDiscount = 0
  for (const p of plans.value) {
    if (p.price_amount && p.annual_price_amount) {
      const discount = Math.round((1 - p.annual_price_amount / (p.price_amount * 12)) * 100)
      if (discount > maxDiscount) maxDiscount = discount
    }
  }
  return maxDiscount || catalog.value?.annual_discount_percent || 0
})
const salesEmail = computed(() => catalog.value?.sales_email || 'support@brevio.com')

const comparisonRows = computed(() => [
  {
    key: 'credits',
    getter: (p: PlanCatalogItem) => formatPlanNumber(p.credits_per_period, locale.value),
  },
  {
    key: 'rollover',
    getter: (p: PlanCatalogItem) => formatPlanNumber(p.rollover_max, locale.value),
  },
  {
    key: 'documents',
    getter: (p: PlanCatalogItem) => formatPlanNumber(p.documents_per_period, locale.value),
  },
  {
    key: 'pagesPerDoc',
    getter: (p: PlanCatalogItem) => formatPlanNumber(p.pages_per_document, locale.value),
  },
  {
    key: 'pagesPeriod',
    getter: (p: PlanCatalogItem) => formatPlanNumber(p.pages_per_period, locale.value),
  },
  {
    key: 'bytesPerDoc',
    getter: (p: PlanCatalogItem) => formatByteSize(p.bytes_per_document, locale.value),
  },
  {
    key: 'bytesPerAudio',
    getter: (p: PlanCatalogItem) => formatByteSize(p.bytes_per_audio, locale.value),
  },
  {
    key: 'bytesPerVideo',
    getter: (p: PlanCatalogItem) => formatByteSize(p.bytes_per_video, locale.value),
  },
  {
    key: 'bytesPeriod',
    getter: (p: PlanCatalogItem) => formatByteSize(p.bytes_per_period, locale.value),
  },
  {
    key: 'concurrent',
    getter: (p: PlanCatalogItem) => formatPlanNumber(p.max_concurrent_jobs, locale.value),
  },
  { key: 'media', getter: (p: PlanCatalogItem) => (p.media_enabled ? t('plans.yes') : t('plans.no')) },
  {
    key: 'youtube',
    getter: (p: PlanCatalogItem) => (p.youtube_enabled ? t('plans.yes') : t('plans.no')),
  },
  { key: 'byok', getter: (p: PlanCatalogItem) => (p.byok_allowed ? t('plans.yes') : t('plans.no')) },
  {
    key: 'models',
    getter: (p: PlanCatalogItem) =>
      p.funds_all_models
        ? t('plans.modelsAll')
        : formatPlanNumber(p.brevio_funded_models.length, locale.value),
  },
  {
    key: 'retention',
    getter: (p: PlanCatalogItem) => t('plans.days', { n: p.retention_days }),
  },
])

const faqItems = computed(() => [
  { title: t('plans.faqCreditsTitle'), body: t('plans.faqCreditsBody') },
  { title: t('plans.faqProductTitle'), body: t('plans.faqProductBody') },
  { title: t('plans.faqExhaustTitle'), body: t('plans.faqExhaustBody') },
  { title: t('plans.faqChangeTitle'), body: t('plans.faqChangeBody') },
  { title: t('plans.faqBillingTitle'), body: t('plans.faqBillingBody') },
])

async function load() {
  loading.value = true
  error.value = null
  try {
    const catalogResult = await plansService.listPlans()
    catalog.value = catalogResult
    const authed = await auth.hydrate()
    if (authed) {
      await auth.fetchProfile().catch(() => undefined)
    }
  } catch (err) {
    error.value = parseApiError(err)
  } finally {
    loading.value = false
  }
}

function isCurrent(plan: PlanCatalogItem): boolean {
  return Boolean(
    isAuthenticated.value && currentPlanId.value && plan.plan_id === currentPlanId.value,
  )
}

function isHighlighted(plan: PlanCatalogItem): boolean {
  return Boolean(plan.highlighted || plan.plan_id === catalog.value?.highlighted_plan_id)
}

function displayAmount(plan: PlanCatalogItem): number | null {
  if (plan.price_amount == null) return null
  if (billingCycle.value === 'year') {
    if (plan.annual_price_amount != null) {
      return Math.round((plan.annual_price_amount / 12) * 100) / 100
    }
  }
  return plan.price_amount
}

function formatMoney(amount: number, currency: string): string {
  return new Intl.NumberFormat(locale.value, {
    style: 'currency',
    currency,
    maximumFractionDigits: amount % 1 === 0 ? 0 : 2,
  }).format(amount)
}

function priceHeadline(plan: PlanCatalogItem): string {
  const amount = displayAmount(plan)
  if (amount == null || !plan.price_currency) return t('plans.priceNotConfigured')
  if (amount === 0) return t('plans.priceFree')
  return formatMoney(amount, plan.price_currency)
}

function ctaLabel(plan: PlanCatalogItem): string {
  if (isCurrent(plan)) return t('plans.ctaCurrent')
  if (plan.trial_days && plan.trial_days > 0) {
    return t('plans.ctaTrial', { name: plan.name, n: plan.trial_days })
  }
  const kind = plan.cta_kind || 'start_free'
  if (kind === 'start_free') return t('plans.ctaStartFree')
  if (kind === 'choose_pro') return t('plans.ctaChoosePro')
  if (kind === 'contact_sales') {
    return isAuthenticated.value ? t('plans.ctaContactSales') : t('plans.ctaContactSales')
  }
  if (isAuthenticated.value && !isCurrent(plan)) return t('plans.ctaUpgrade')
  return t('plans.ctaChoosePlan', { name: plan.name })
}

async function onCta(plan: PlanCatalogItem) {
  if (isCurrent(plan)) return
  const kind = plan.cta_kind || 'start_free'
  if (kind === 'contact_sales') {
    window.location.href = `mailto:${salesEmail.value}?subject=${encodeURIComponent(`Brevio ${plan.name}`)}`
    return
  }
  if (!isAuthenticated.value) {
    goRegister()
    return
  }
  
  if (plan.plan_id === 'free') {
    // Cannot "checkout" to a free plan, redirect to profile or handle free downgrade
    router.push({ name: 'profile' })
    return
  }
  
  try {
    loading.value = true
    const successUrl = `${window.location.origin}/profile?session_id={CHECKOUT_SESSION_ID}`
    const cancelUrl = window.location.href
    
    const { url } = await plansService.createCheckoutSession(
      plan.plan_id,
      billingCycle.value,
      successUrl,
      cancelUrl
    )
    window.location.href = url
  } catch (err) {
    error.value = parseApiError(err)
  } finally {
    loading.value = false
  }
}

function goProfile() {
  router.push({ name: 'profile' })
}

function goRegister() {
  router.push({ name: 'register', query: { redirect: '/plans' } })
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: '/plans' } })
}

onMounted(load)
</script>

<template>
  <div class="plans-page" data-testid="plans-view">
    <header class="plans-hero">
      <p class="eyebrow">{{ t('nav.plans') }}</p>
      <h1>{{ t('plans.title') }}</h1>
      <p class="lede">{{ t('plans.subtitle') }}</p>

      <div
        v-if="showBillingToggle"
        class="billing-toggle"
        role="group"
        :aria-label="t('plans.billingToggleMonthly')"
        data-testid="plans-billing-toggle"
      >
        <button
          type="button"
          class="toggle-btn"
          :class="{ active: billingCycle === 'month' }"
          :aria-pressed="billingCycle === 'month'"
          @click="billingCycle = 'month'"
        >
          {{ t('plans.billingToggleMonthly') }}
        </button>
        <button
          type="button"
          class="toggle-btn"
          :class="{ active: billingCycle === 'year' }"
          :aria-pressed="billingCycle === 'year'"
          data-testid="plans-toggle-annual"
          @click="billingCycle = 'year'"
        >
          {{ t('plans.billingToggleAnnual') }}
          <span v-if="annualDiscount > 0" class="save-pill">{{ t('plans.billingToggleSave', { percent: annualDiscount }) }}</span>
        </button>
      </div>
    </header>

    <StateBlock :loading="loading" :error="error" @retry="load">
      <div class="plans-content">
        <section
          v-if="entitlements"
          class="usage-strip"
          data-testid="plans-current"
          aria-labelledby="plans-current-heading"
        >
          <div class="usage-strip-head">
            <h2 id="plans-current-heading">{{ t('plans.yourPlan') }}</h2>
            <span class="chip">{{ entitlements.plan_name }}</span>
          </div>
          <div class="usage-grid">
            <div>
              <span class="muted">{{ t('plans.periodWindow') }}</span>
              <p>
                {{ formatPeriodDate(entitlements.period_start, locale) }}
                –
                {{ formatPeriodDate(entitlements.period_end, locale) }}
              </p>
            </div>
            <div>
              <span class="muted">{{ t('plans.creditsRemaining') }}</span>
              <p>
                {{ formatPlanNumber(entitlements.remaining.credits, locale) }}
                /
                {{ formatPlanNumber(entitlements.limits.credits_per_period, locale) }}
              </p>
            </div>
            <div>
              <span class="muted">{{ t('plans.documentsRemaining') }}</span>
              <p>
                {{ formatPlanNumber(entitlements.remaining.documents, locale) }}
                /
                {{ formatPlanNumber(entitlements.limits.documents_per_period, locale) }}
              </p>
            </div>
            <div>
              <span class="muted">{{ t('plans.pagesRemaining') }}</span>
              <p>
                {{ formatPlanNumber(entitlements.remaining.pages, locale) }}
                /
                {{ formatPlanNumber(entitlements.limits.pages_per_period, locale) }}
              </p>
            </div>
          </div>
        </section>

        <p v-if="!isAuthenticated" class="guest-line" data-testid="plans-guest-notice">
          {{ t('plans.guestNotice') }}
        </p>

        <section class="tier-grid" :aria-label="t('plans.catalogLabel')" data-testid="plans-grid">
          <article
            v-for="plan in plans"
            :key="plan.plan_id"
            class="tier-card"
            :class="{
              highlighted: isHighlighted(plan) && !isCurrent(plan),
              current: isCurrent(plan),
            }"
            :data-testid="`plan-card-${plan.plan_id}`"
            :aria-current="isCurrent(plan) ? 'true' : undefined"
          >
            <div class="tier-top">
              <div class="tier-name-row">
                <h2>{{ plan.name }}</h2>
                <span v-if="isCurrent(plan)" class="badge current">{{ t('plans.currentBadge') }}</span>
                <span v-else-if="isHighlighted(plan)" class="badge popular" data-testid="plan-popular-badge">
                  {{ t('plans.popularBadge') }}
                </span>
              </div>

              <div class="price-block" data-testid="plan-price">
                <p class="price-figure">{{ priceHeadline(plan) }}</p>
                <p v-if="displayAmount(plan) && displayAmount(plan)! > 0" class="price-meta">
                  <span>{{ t('plans.pricePerMonth') }}</span>
                  <span v-if="billingCycle === 'year'"> · {{ t('plans.priceBilledAnnually') }}</span>
                </p>
                <p class="price-note">{{ t('plans.billingFlexible') }}</p>
              </div>
            </div>

            <ul class="benefit-list">
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{
                  t('plans.benefitCredits', {
                    n: formatPlanNumber(plan.credits_per_period, locale),
                  })
                }}</span>
              </li>
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{
                  t('plans.benefitRollover', {
                    n: formatPlanNumber(plan.rollover_max, locale),
                  })
                }}</span>
              </li>
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{
                  t('plans.benefitDocuments', {
                    n: formatPlanNumber(plan.documents_per_period, locale),
                  })
                }}</span>
              </li>
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{
                  t('plans.benefitPagesDoc', {
                    n: formatPlanNumber(plan.pages_per_document, locale),
                  })
                }}</span>
              </li>
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{
                  t('plans.benefitPagesPeriod', {
                    n: formatPlanNumber(plan.pages_per_period, locale),
                  })
                }}</span>
              </li>
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{
                  t('plans.benefitDocSize', {
                    size: formatByteSize(plan.bytes_per_document, locale),
                  })
                }}</span>
              </li>
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{
                  t('plans.benefitAudioSize', {
                    size: formatByteSize(plan.bytes_per_audio, locale),
                  })
                }}</span>
              </li>
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{
                  t('plans.benefitVideoSize', {
                    size: formatByteSize(plan.bytes_per_video, locale),
                  })
                }}</span>
              </li>
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{
                  t('plans.benefitConcurrent', {
                    n: formatPlanNumber(plan.max_concurrent_jobs, locale),
                  })
                }}</span>
                <button
                  type="button"
                  class="tip"
                  v-tooltip.top="t('plans.tipConcurrent')"
                  :aria-label="t('plans.tipConcurrent')"
                >
                  <HelpCircle :size="14" :stroke-width="2" />
                </button>
              </li>
              <li :class="{ muted: !plan.media_enabled }">
                <component
                  :is="plan.media_enabled ? Check : Minus"
                  :class="plan.media_enabled ? 'ok' : 'off'"
                  :size="18"
                  :stroke-width="2.5"
                  aria-hidden="true"
                />
                <span>{{ plan.media_enabled ? t('plans.benefitMediaOn') : t('plans.benefitMediaOff') }}</span>
              </li>
              <li :class="{ muted: !plan.youtube_enabled }">
                <component
                  :is="plan.youtube_enabled ? Check : Minus"
                  :class="plan.youtube_enabled ? 'ok' : 'off'"
                  :size="18"
                  :stroke-width="2.5"
                  aria-hidden="true"
                />
                <span>{{
                  plan.youtube_enabled ? t('plans.benefitYoutubeOn') : t('plans.benefitYoutubeOff')
                }}</span>
              </li>
              <li :class="{ muted: !plan.byok_allowed }">
                <component
                  :is="plan.byok_allowed ? Check : Minus"
                  :class="plan.byok_allowed ? 'ok' : 'off'"
                  :size="18"
                  :stroke-width="2.5"
                  aria-hidden="true"
                />
                <span>{{ plan.byok_allowed ? t('plans.benefitByokOn') : t('plans.benefitByokOff') }}</span>
                <button
                  type="button"
                  class="tip"
                  v-tooltip.top="t('plans.tipByok')"
                  :aria-label="t('plans.tipByok')"
                >
                  <HelpCircle :size="14" :stroke-width="2" />
                </button>
              </li>
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{
                  plan.funds_all_models
                    ? t('plans.benefitModelsAll')
                    : t('plans.benefitModelsList', { n: plan.brevio_funded_models.length })
                }}</span>
                <button
                  type="button"
                  class="tip"
                  v-tooltip.top="t('plans.tipModels')"
                  :aria-label="t('plans.tipModels')"
                >
                  <HelpCircle :size="14" :stroke-width="2" />
                </button>
              </li>
              <li>
                <Check class="ok" :size="18" :stroke-width="2.5" aria-hidden="true" />
                <span>{{ t('plans.benefitRetention', { n: plan.retention_days }) }}</span>
                <button
                  type="button"
                  class="tip"
                  v-tooltip.top="t('plans.tipRetention')"
                  :aria-label="t('plans.tipRetention')"
                >
                  <HelpCircle :size="14" :stroke-width="2" />
                </button>
              </li>
            </ul>

            <div class="tier-cta">
              <Button
                :label="ctaLabel(plan)"
                :disabled="isCurrent(plan)"
                :severity="isHighlighted(plan) && !isCurrent(plan) ? undefined : 'secondary'"
                :outlined="!isHighlighted(plan) && !isCurrent(plan)"
                class="w-full"
                :data-testid="
                  isCurrent(plan)
                    ? 'plan-cta-current'
                    : !isAuthenticated
                      ? 'plan-cta-register'
                      : `plan-cta-${plan.cta_kind || 'choose'}`
                "
                @click="onCta(plan)"
              />
            </div>
          </article>
        </section>

        <p class="list-price-note" data-testid="plans-no-checkout">{{ t('plans.listPriceNote') }}</p>

        <section class="byok-card" aria-labelledby="plans-byok-card-heading">
          <div class="byok-icon" aria-hidden="true">
            <KeyRound :size="22" :stroke-width="2" />
          </div>
          <div class="byok-copy">
            <h2 id="plans-byok-card-heading">{{ t('plans.byokCardTitle') }}</h2>
            <p>{{ t('plans.byokCardBody') }}</p>
          </div>
          <Button
            v-if="isAuthenticated"
            :label="t('plans.byokCta')"
            severity="secondary"
            outlined
            data-testid="plans-byok-cta"
            @click="goProfile"
          />
          <Button
            v-else
            :label="t('plans.byokCtaGuest')"
            severity="secondary"
            outlined
            data-testid="plans-guest-register"
            @click="goRegister"
          />
        </section>

        <section class="compare-section" data-testid="plans-compare">
          <button
            type="button"
            class="compare-toggle"
            :aria-expanded="compareOpen"
            data-testid="plans-compare-toggle"
            @click="compareOpen = !compareOpen"
          >
            <span>{{ compareOpen ? t('plans.compareToggleHide') : t('plans.compareToggleShow') }}</span>
            <ChevronDown :size="18" :class="{ open: compareOpen }" aria-hidden="true" />
          </button>

          <div v-show="compareOpen" class="compare-panel">
            <h2>{{ t('plans.compareTitle') }}</h2>
            <p class="muted">{{ t('plans.compareIntro') }}</p>
            <div class="compare-scroll" role="region" :aria-label="t('plans.compareTitle')" tabindex="0">
              <table class="compare-table">
                <thead>
                  <tr>
                    <th scope="col">{{ t('plans.compareFeature') }}</th>
                    <th v-for="plan in plans" :key="plan.plan_id" scope="col">{{ plan.name }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in comparisonRows" :key="row.key">
                    <th scope="row">{{ t(`plans.compare.${row.key}`) }}</th>
                    <td v-for="plan in plans" :key="`${row.key}-${plan.plan_id}`">
                      {{ row.getter(plan) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section class="faq-section" aria-labelledby="plans-faq-heading">
          <h2 id="plans-faq-heading">{{ t('plans.faqTitle') }}</h2>
          <Accordion multiple>
            <AccordionPanel v-for="(item, index) in faqItems" :key="item.title" :value="String(index)">
              <AccordionHeader>{{ item.title }}</AccordionHeader>
              <AccordionContent>
                <p class="faq-body">{{ item.body }}</p>
              </AccordionContent>
            </AccordionPanel>
          </Accordion>
          <p v-if="!isAuthenticated" class="faq-signin">
            <button type="button" class="text-link" data-testid="plan-cta-login" @click="goLogin">
              {{ t('plans.ctaSignIn') }}
            </button>
          </p>
        </section>
      </div>
    </StateBlock>
  </div>
</template>

<style scoped>
.plans-page {
  display: grid;
  gap: 3rem;
  padding-block: 0.5rem 2.5rem;
  max-width: 1120px;
  margin-inline: auto;
}

.plans-hero {
  text-align: center;
  display: grid;
  gap: 1rem;
  justify-items: center;
}

.eyebrow {
  margin: 0;
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--bv-primary-strong);
}

.plans-hero h1 {
  margin: 0;
  font-family: var(--bv-font-sans);
  font-size: clamp(1.75rem, 3.2vw, 2rem);
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--bv-ink);
  max-width: 18ch;
}

.lede {
  margin: 0;
  max-width: 40rem;
  font-size: 1rem;
  line-height: 1.55;
  color: var(--bv-ink-soft);
}

.billing-toggle {
  display: inline-flex;
  gap: 0.25rem;
  padding: 0.25rem;
  border-radius: 999px;
  background: #eef3f6;
  border: 1px solid var(--bv-border);
}

.toggle-btn {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--bv-ink-soft);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 600;
  padding: 0.55rem 0.95rem;
  border-radius: 999px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.toggle-btn.active {
  background: #fff;
  color: var(--bv-ink);
  box-shadow: var(--bv-shadow-sm);
}

.save-pill {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--bv-primary-strong);
  background: var(--bv-primary-soft);
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
}

.guest-line {
  margin: 0;
  text-align: center;
  color: var(--bv-ink-soft);
  font-size: 0.95rem;
  line-height: 1.5;
}

.usage-strip {
  background: #fff;
  border: 1px solid var(--bv-border);
  border-radius: var(--bv-radius);
  padding: 1.5rem;
  box-shadow: var(--bv-shadow-sm);
}

.usage-strip-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.usage-strip-head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 650;
}

.chip {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: var(--bv-primary-soft);
  color: var(--bv-primary-strong);
}

.usage-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10.5rem, 1fr));
  gap: 1rem;
}

.usage-grid p {
  margin: 0.25rem 0 0;
  font-weight: 650;
  color: var(--bv-ink);
}

.muted {
  color: var(--bv-ink-muted);
  font-size: 0.8125rem;
}

.tier-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
  align-items: stretch;
}

.tier-card {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  background: #fff;
  border: 1px solid var(--bv-border);
  border-radius: 1.25rem;
  padding: 1.75rem 1.5rem;
  box-shadow: var(--bv-shadow-sm);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.tier-card.highlighted {
  border-color: var(--bv-primary);
  box-shadow:
    0 0 0 1px rgba(31, 184, 168, 0.25),
    0 18px 40px rgba(7, 45, 45, 0.12);
  transform: translateY(-4px);
}

.tier-card.current {
  border-color: var(--bv-border-strong);
}

.tier-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.tier-name-row h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 650;
  color: var(--bv-ink);
}

.badge {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
}

.badge.popular {
  background: var(--bv-sidebar);
  color: #ecfdf8;
}

.badge.current {
  background: var(--bv-bg-muted);
  color: var(--bv-ink-soft);
}

.price-block {
  display: grid;
  gap: 0.25rem;
}

.price-figure {
  margin: 0;
  font-size: 2.25rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--bv-ink);
  line-height: 1.1;
}

.price-meta {
  margin: 0;
  font-size: 0.875rem;
  color: var(--bv-ink-muted);
}

.price-note {
  margin: 0.35rem 0 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--bv-ink-muted);
}

.benefit-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.7rem;
  flex: 1;
}

.benefit-list li {
  display: grid;
  grid-template-columns: 1.15rem 1fr auto;
  gap: 0.55rem;
  align-items: start;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--bv-ink-soft);
}

.benefit-list li.muted {
  color: var(--bv-ink-muted);
}

.ok {
  color: var(--bv-success);
  margin-top: 0.1rem;
}

.off {
  color: #b6c4cc;
  margin-top: 0.1rem;
}

.tip {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--bv-ink-muted);
  padding: 0;
  cursor: help;
  display: inline-flex;
  margin-top: 0.15rem;
}

.tier-cta {
  margin-top: auto;
  padding-top: 0.5rem;
}

.w-full {
  width: 100%;
}

.plans-content {
  display: grid;
  gap: 3rem;
}

.list-price-note {
  margin: 0;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--bv-ink-muted);
}

.byok-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 1rem;
  align-items: center;
  background: linear-gradient(135deg, #f3fbfa 0%, #fff 60%);
  border: 1px solid #cfe8e4;
  border-radius: var(--bv-radius);
  padding: 1.25rem 1.5rem;
}

.byok-icon {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 0.85rem;
  display: grid;
  place-items: center;
  background: var(--bv-primary-soft);
  color: var(--bv-primary-strong);
}

.byok-copy h2 {
  margin: 0 0 0.35rem;
  font-size: 1rem;
  font-weight: 650;
}

.byok-copy p {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--bv-ink-soft);
}

.compare-section {
  display: grid;
  gap: 1rem;
}

.compare-toggle {
  appearance: none;
  border: 1px solid var(--bv-border);
  background: #fff;
  border-radius: 999px;
  padding: 0.7rem 1.1rem;
  font: inherit;
  font-weight: 600;
  color: var(--bv-ink);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: fit-content;
  margin-inline: auto;
}

.compare-toggle svg {
  transition: transform 0.2s ease;
}

.compare-toggle svg.open {
  transform: rotate(180deg);
}

.compare-panel {
  background: #fff;
  border: 1px solid var(--bv-border);
  border-radius: var(--bv-radius);
  padding: 1.5rem;
  display: grid;
  gap: 0.75rem;
}

.compare-panel h2 {
  margin: 0;
  font-size: 1.125rem;
}

.compare-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border: 1px solid var(--bv-border);
  border-radius: var(--bv-radius-sm);
}

.compare-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 36rem;
  font-size: 0.9rem;
}

.compare-table th,
.compare-table td {
  padding: 0.85rem 1rem;
  text-align: start;
  border-bottom: 1px solid var(--bv-border);
}

.compare-table thead th {
  position: sticky;
  top: 0;
  background: #f1f5f7;
  z-index: 1;
  font-weight: 650;
}

.compare-table tbody tr:nth-child(even) {
  background: #fafcfd;
}

.compare-table tbody th {
  font-weight: 600;
  color: var(--bv-ink);
  white-space: nowrap;
}

.faq-section {
  display: grid;
  gap: 1rem;
}

.faq-section h2 {
  margin: 0;
  font-size: 1.25rem;
  text-align: center;
}

.faq-body {
  margin: 0;
  color: var(--bv-ink-soft);
  line-height: 1.55;
  font-size: 0.9375rem;
}

.faq-signin {
  margin: 0;
  text-align: center;
}

.text-link {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--bv-primary-strong);
  font: inherit;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 0.15em;
  cursor: pointer;
}

@media (max-width: 960px) {
  .tier-grid {
    grid-template-columns: 1fr;
  }

  .tier-card.highlighted {
    transform: none;
  }

  .byok-card {
    grid-template-columns: auto 1fr;
  }

  .byok-card :deep(.p-button) {
    grid-column: 1 / -1;
  }

  .plans-hero h1 {
    max-width: none;
  }
}
</style>
