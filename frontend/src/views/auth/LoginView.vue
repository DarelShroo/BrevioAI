<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Message from 'primevue/message'
import { useAuthStore } from '@/stores/auth.store'
import { parseApiError } from '@/utils/errors'
import { validateIdentity } from '@/utils/validation'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const form = reactive({
  identity: '',
  password: '',
})
const error = ref<string | null>(null)
const fieldErrors = reactive({ identity: '', password: '' })

const canSubmit = computed(() => !auth.loading)

async function onSubmit() {
  error.value = null
  fieldErrors.identity =
    validateIdentity(form.identity) || (form.identity.trim() ? '' : t('validation.identityRequired'))
  fieldErrors.password = form.password ? '' : t('validation.passwordRequired')
  if (fieldErrors.identity || fieldErrors.password) return

  try {
    await auth.login({
      identity: form.identity.trim(),
      password: form.password,
    })
    const redirect =
      typeof router.currentRoute.value.query.redirect === 'string'
        ? router.currentRoute.value.query.redirect
        : '/summary'
    await router.replace(redirect)
  } catch (err) {
    error.value = parseApiError(err, t('auth.loginFailed'))
  }
}
</script>

<template>
  <form class="stack" @submit.prevent="onSubmit" data-testid="login-form">
    <div>
      <h2>{{ t('auth.welcomeBack') }}</h2>
      <p class="muted">{{ t('auth.signInHint') }}</p>
    </div>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div class="stack">
      <label for="login-identity">{{ t('auth.identity') }}</label>
      <InputText
        id="login-identity"
        v-model="form.identity"
        autocomplete="username"
        aria-required="true"
        data-testid="login-identity"
        :invalid="!!fieldErrors.identity"
      />
      <small v-if="fieldErrors.identity" class="error">{{ fieldErrors.identity }}</small>
    </div>

    <div class="stack">
      <label for="login-password">{{ t('auth.password') }}</label>
      <Password
        input-id="login-password"
        v-model="form.password"
        :feedback="false"
        toggle-mask
        autocomplete="current-password"
        input-class="w-full"
        class="w-full"
        :pt="{ pcInputText: { root: { 'data-testid': 'login-password' } } }"
        :invalid="!!fieldErrors.password"
      />
      <small v-if="fieldErrors.password" class="error">{{ fieldErrors.password }}</small>
    </div>

    <Button
      type="submit"
      :label="t('auth.signIn')"
      :loading="auth.loading"
      :disabled="!canSubmit"
      data-testid="login-submit"
    />

    <div class="links">
      <RouterLink :to="{ name: 'register' }" class="auth-link flex-center">
        <i class="pi pi-check-square" style="margin-right: 0.4rem; color: var(--bv-primary)"></i>
        {{ t('auth.createAccount') }}
      </RouterLink>
      <RouterLink :to="{ name: 'password-recovery' }" class="auth-link">{{ t('auth.forgotPassword') }}</RouterLink>
    </div>

    <div class="divider">
      <span class="circle"></span>
    </div>

    <div class="bottom-links">
      <RouterLink class="demo-link flex-center" :to="{ name: 'plans' }" data-testid="login-plans-link">
        {{ t('nav.plans') }} <i class="pi pi-chevron-right" style="font-size: 0.75rem; margin-left: 0.4rem"></i>
      </RouterLink>
      <RouterLink class="demo-link flex-center" :to="{ name: 'comparar' }" data-testid="login-demo-link">
        {{ t('demo.badge') }} <i class="pi pi-chevron-right" style="font-size: 0.75rem; margin-left: 0.4rem"></i>
      </RouterLink>
    </div>
  </form>
</template>

<style scoped>
.links {
  display: flex;
  justify-content: space-between;
  gap: var(--bv-space-3);
  flex-wrap: wrap;
  margin-top: var(--bv-space-2);
}

.auth-link {
  color: var(--bv-primary);
  font-weight: 500;
  text-decoration: none;
  font-size: 0.95rem;
}

.auth-link:hover {
  text-decoration: underline;
}

.flex-center {
  display: flex;
  align-items: center;
}

.divider {
  display: flex;
  align-items: center;
  margin: var(--bv-space-4) 0;
  opacity: 0.6;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid var(--bv-border-color, #e2e8f0);
}

.divider .circle {
  width: 6px;
  height: 6px;
  border: 1px solid var(--bv-border-color, #a0aec0);
  border-radius: 50%;
  margin: 0 var(--bv-space-3);
  background-color: transparent;
}

.bottom-links {
  display: flex;
  justify-content: space-between;
  gap: var(--bv-space-3);
  flex-wrap: wrap;
}

.demo-link {
  color: var(--bv-primary);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.95rem;
}

.demo-link:hover {
  text-decoration: underline;
}

.error {
  color: var(--bv-danger);
}

.w-full {
  width: 100%;
}

:deep(.p-password) {
  width: 100%;
}

:deep(.p-password-input) {
  width: 100%;
}
</style>
