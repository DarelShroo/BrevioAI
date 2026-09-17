<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import StateBlock from '@/components/common/StateBlock.vue'
import * as credentialsService from '@/services/credentials.service'
import * as plansService from '@/services/plans.service'
import { useAuthStore } from '@/stores/auth.store'
import { useCatalogStore } from '@/stores/catalog.store'
import { useAppToast } from '@/composables/useToast'
import type { UserCredential } from '@/types/user'
import { parseApiError } from '@/utils/errors'
import { providerLabel } from '@/utils/labels'

const FALLBACK_PAID_PROVIDERS = ['openai', 'deepseek', 'google', 'xai', 'anthropic']

const { t, te } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const catalog = useCatalogStore()
const toast = useAppToast()

const loading = ref(false)
const syncingBilling = ref(false)
const error = ref<string | null>(null)
const credentials = ref<UserCredential[]>([])
const providerFilter = ref('openai')
const updatingDefaultId = ref<string | null>(null)
const renamingId = ref<string | null>(null)
const managingBilling = ref(false)

const isPremium = computed(() => {
  const planId = auth.profile?.plan_id || auth.profile?.entitlements?.plan_id
  return planId && planId !== 'free'
})

const paidProviders = computed(() => {
  const fromCatalog = catalog.paidProviders.map((item) => item.id)
  return fromCatalog.length ? fromCatalog : FALLBACK_PAID_PROVIDERS
})
const providerOptions = computed(() =>
  paidProviders.value.map((id) => ({
    label: providerLabel(id, t, te),
    value: id,
  })),
)

const form = reactive({
  provider: 'openai',
  name: '',
  api_key: '',
  is_default: false,
})
const saving = ref(false)
const formResetKey = ref(0)

function clearCredentialForm(keepProvider = true) {
  const provider = keepProvider
    ? form.provider
    : paidProviders.value[0] || 'openai'
  form.provider = provider
  form.name = ''
  form.api_key = ''
  form.is_default = false
  formResetKey.value += 1
}

function displayName(item: UserCredential): string {
  return credentialsService.credentialDisplayName(item, t('profile.unnamedCredential'))
}

async function loadProfile() {
  loading.value = true
  error.value = null
  try {
    await Promise.all([auth.fetchProfile(), catalog.loadAll().catch(() => undefined)])
    if (!paidProviders.value.includes(providerFilter.value)) {
      providerFilter.value = paidProviders.value[0] || 'openai'
    }
    if (!paidProviders.value.includes(form.provider)) {
      form.provider = paidProviders.value[0] || 'openai'
    }
    await loadCredentials()
  } catch (err) {
    error.value = parseApiError(err)
  } finally {
    loading.value = false
  }
}

async function syncAfterCheckout() {
  const sessionId = typeof route.query.session_id === 'string' ? route.query.session_id : ''
  if (!sessionId) return
  syncingBilling.value = true
  try {
    // Webhooks can lag; pull Stripe Checkout session / subscription into local plan+credits.
    await plansService.syncBillingState(sessionId).catch(() => undefined)
    for (let i = 0; i < 6; i += 1) {
      await auth.fetchProfile().catch(() => undefined)
      const planId = auth.profile?.plan_id || auth.profile?.entitlements?.plan_id
      const credits = Number(auth.profile?.user_credit ?? 0)
      if (planId && planId !== 'free' && credits > 0) break
      await new Promise((r) => setTimeout(r, 800))
      await plansService.syncBillingState(sessionId).catch(() => undefined)
    }
    toast.success(t('profile.billingSynced'))
    await router.replace({ name: 'profile', query: {} })
  } finally {
    syncingBilling.value = false
  }
}

onMounted(async () => {
  await loadProfile()
  await syncAfterCheckout()
})

async function manageBilling() {
  managingBilling.value = true
  try {
    const { url } = await plansService.createPortalSession(window.location.href)
    window.location.href = url
  } catch (err) {
    toast.error(parseApiError(err))
  } finally {
    managingBilling.value = false
  }
}

async function loadCredentials() {
  try {
    credentials.value = await credentialsService.listCredentials(providerFilter.value)
  } catch (err) {
    credentials.value = []
    const message = parseApiError(err)
    if (!message.toLowerCase().includes('not found')) {
      toast.warn(message)
    }
  }
}

async function saveCredential() {
  if (!form.name.trim()) {
    toast.error(t('profile.credentialNameRequired'))
    return
  }
  if (!form.api_key.trim()) {
    toast.error(t('profile.apiKeyRequired'))
    return
  }
  saving.value = true
  try {
    await credentialsService.createCredential({
      provider: form.provider,
      name: form.name.trim(),
      api_key: form.api_key.trim(),
      is_default: form.is_default,
    })
    providerFilter.value = form.provider
    clearCredentialForm(true)
    toast.success(t('profile.credentialSaved'))
    await loadCredentials()
  } catch (err) {
    toast.error(parseApiError(err))
  } finally {
    saving.value = false
  }
}

async function makeDefault(item: UserCredential) {
  const id = credentialsService.credentialId(item)
  if (!id || item.is_default) return
  updatingDefaultId.value = id
  try {
    await credentialsService.setDefaultCredential(id)
    toast.success(t('profile.defaultUpdated'))
    await loadCredentials()
  } catch (err) {
    toast.error(parseApiError(err))
  } finally {
    updatingDefaultId.value = null
  }
}

async function renameCredential(item: UserCredential) {
  const id = credentialsService.credentialId(item)
  if (!id) return
  const current = displayName(item)
  const next = window.prompt(t('profile.renameCredentialPrompt'), item.name || current)
  if (next == null) return
  const cleaned = next.trim()
  if (!cleaned) {
    toast.error(t('profile.credentialNameRequired'))
    return
  }
  if (cleaned === (item.name || '').trim()) return
  renamingId.value = id
  try {
    await credentialsService.renameCredential(id, { name: cleaned })
    toast.success(t('profile.credentialRenamed'))
    await loadCredentials()
  } catch (err) {
    toast.error(parseApiError(err))
  } finally {
    renamingId.value = null
  }
}

async function removeCredential(item: UserCredential) {
  const id = credentialsService.credentialId(item)
  if (!id) {
    toast.error(t('errors.notFound'))
    return
  }
  try {
    await credentialsService.deleteCredential(id)
    toast.success(t('profile.credentialRemoved'))
    await loadCredentials()
  } catch (err) {
    toast.error(parseApiError(err))
  }
}

watch(providerFilter, () => {
  void loadCredentials()
})
</script>

<template>
  <div class="stack profile-view" data-testid="profile-view">
    <section class="card-surface panel">
      <StateBlock :loading="(loading || syncingBilling) && !auth.profile" :error="error">
        <div v-if="auth.profile" class="stack">
          <p v-if="syncingBilling" class="muted" data-testid="billing-syncing">
            {{ t('profile.billingSyncing') }}
          </p>
          <h2>{{ auth.profile.username }}</h2>
          <div class="field-grid">
            <div>
              <span class="muted">{{ t('profile.email') }}</span>
              <p>{{ auth.profile.email }}</p>
            </div>
            <div>
              <span class="muted">{{ t('profile.userId') }}</span>
              <p>{{ auth.profile.id }}</p>
            </div>
            <div>
              <span class="muted">{{ t('profile.plan') }}</span>
              <p>{{ auth.profile.plan_name || auth.profile.plan_id || '—' }}</p>
            </div>
            <div>
              <span class="muted">{{ t('profile.credits') }}</span>
              <p>{{ auth.profile.user_credit }}</p>
            </div>
            <div v-if="auth.profile.entitlements">
              <span class="muted">{{ t('profile.documentsRemaining') }}</span>
              <p>
                {{ auth.profile.entitlements.remaining.documents }}
                /
                {{ auth.profile.entitlements.limits.documents_per_period }}
              </p>
            </div>
            <div v-if="auth.profile.entitlements">
              <span class="muted">{{ t('profile.pagesRemaining') }}</span>
              <p>
                {{ auth.profile.entitlements.remaining.pages }}
                /
                {{ auth.profile.entitlements.limits.pages_per_period }}
              </p>
            </div>
            <div v-if="auth.profile.entitlements">
              <span class="muted">{{ t('profile.creditsRemaining') }}</span>
              <p>
                {{ auth.profile.entitlements.remaining.credits }}
                /
                {{ auth.profile.entitlements.limits.credits_per_period }}
              </p>
            </div>
            <div>
              <span class="muted">{{ t('profile.folder') }}</span>
              <p>{{ auth.profile.folder_id || '—' }}</p>
            </div>
          </div>
          <div class="row" style="gap: 1rem">
            <RouterLink :to="{ name: 'plans' }" data-testid="profile-plans-link">
              <Button :label="t('pages.plans')" severity="secondary" />
            </RouterLink>
            <Button
              v-if="isPremium"
              label="Manage Billing"
              icon="pi pi-credit-card"
              :loading="managingBilling"
              @click="manageBilling"
            />
          </div>
          <RouterLink :to="{ name: 'password-recovery' }">{{ t('profile.changePassword') }}</RouterLink>
        </div>
      </StateBlock>
    </section>

    <section class="card-surface panel stack">
      <div class="row" style="justify-content: space-between; flex-wrap: wrap">
        <h2>{{ t('profile.credentials') }}</h2>
        <div class="row">
          <Select
            v-model="providerFilter"
            :options="providerOptions"
            option-label="label"
            option-value="value"
            :aria-label="t('profile.providerFilter')"
          />
          <Button :label="t('profile.refresh')" severity="secondary" text @click="loadCredentials" />
        </div>
      </div>

      <Message severity="info" :closable="false">
        {{ t('profile.credentialsIntro') }}
      </Message>

      <DataTable :value="credentials" :empty-message="t('profile.noCredentials')">
        <Column field="name" :header="t('profile.credentialName')">
          <template #body="{ data }">
            <div class="name-cell">
              <strong>{{ displayName(data) }}</strong>
              <Button
                :label="t('profile.rename')"
                text
                size="small"
                class="rename-btn"
                :loading="renamingId === credentialsService.credentialId(data)"
                :disabled="!credentialsService.credentialId(data)"
                data-testid="credential-rename"
                @click="renameCredential(data)"
              />
            </div>
          </template>
        </Column>
        <Column field="provider" :header="t('profile.provider')">
          <template #body="{ data }">
            {{ providerLabel(data.provider, t, te) }}
          </template>
        </Column>
        <Column field="status" :header="t('profile.status')" />
        <Column :header="t('profile.default')">
          <template #body="{ data }">
            <Tag
              v-if="data.is_default"
              :value="t('profile.defaultBadge')"
              severity="success"
              data-testid="credential-default-badge"
            />
            <Button
              v-else
              :label="t('profile.makeDefault')"
              text
              size="small"
              :loading="updatingDefaultId === credentialsService.credentialId(data)"
              :disabled="!credentialsService.credentialId(data)"
              data-testid="credential-make-default"
              @click="makeDefault(data)"
            />
          </template>
        </Column>
        <Column header="">
          <template #body="{ data }">
            <Button
              :label="t('profile.delete')"
              severity="danger"
              text
              size="small"
              :disabled="!credentialsService.credentialId(data)"
              data-testid="credential-delete"
              @click="removeCredential(data)"
            />
          </template>
        </Column>
      </DataTable>

      <form class="stack form" @submit.prevent="saveCredential">
        <h3>{{ t('profile.addCredential') }}</h3>
        <Message severity="info" :closable="false">
          {{ t('profile.keysHint') }}
        </Message>
        <div :key="formResetKey" class="field-grid">
          <div class="stack">
            <label for="cred-provider">{{ t('profile.provider') }}</label>
            <Select
              input-id="cred-provider"
              v-model="form.provider"
              :options="providerOptions"
              option-label="label"
              option-value="value"
            />
          </div>
          <div class="stack">
            <label for="cred-name">{{ t('profile.credentialName') }}</label>
            <InputText
              id="cred-name"
              v-model="form.name"
              class="w-full"
              maxlength="80"
              autocomplete="off"
              :placeholder="t('profile.credentialNamePlaceholder')"
              data-testid="credential-name"
            />
          </div>
          <div class="stack">
            <label for="cred-key">{{ t('profile.apiKey') }}</label>
            <InputText
              id="cred-key"
              v-model="form.api_key"
              type="password"
              autocomplete="new-password"
              class="w-full"
              data-testid="credential-api-key"
            />
          </div>
        </div>
        <div :key="`default-${formResetKey}`" class="row">
          <Checkbox v-model="form.is_default" binary input-id="cred-default" />
          <label for="cred-default">{{ t('profile.setDefault') }}</label>
        </div>
        <Button type="submit" :label="t('profile.saveCredential')" :loading="saving" />
      </form>
    </section>
  </div>
</template>

<style scoped>
.panel {
  padding: var(--bv-space-5);
}

.w-full {
  width: 100%;
}

:deep(.p-password),
:deep(.p-password-input) {
  width: 100%;
}

.form {
  border-top: 1px solid var(--bv-border);
  padding-top: var(--bv-space-4);
}

.name-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
}

.rename-btn {
  padding-inline: 0;
}
</style>
