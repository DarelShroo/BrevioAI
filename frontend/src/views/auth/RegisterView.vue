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
import { isValidEmail, validatePassword, validateUsername } from '@/utils/validation'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const form = reactive({
  username: '',
  email: '',
  password: '',
})
const error = ref<string | null>(null)
const fieldErrors = reactive({ username: '', email: '', password: '' })

const canSubmit = computed(
  () =>
    form.username.trim().length > 0 &&
    form.email.trim().length > 0 &&
    form.password.length > 0 &&
    !auth.loading,
)

async function onSubmit() {
  error.value = null
  fieldErrors.username = validateUsername(form.username) || ''
  fieldErrors.email = isValidEmail(form.email) ? '' : t('validation.validEmail')
  fieldErrors.password = validatePassword(form.password) || ''
  if (fieldErrors.username || fieldErrors.email || fieldErrors.password) return

  try {
    await auth.register({
      username: form.username.trim(),
      email: form.email.trim(),
      password: form.password,
    })
    const redirect =
      typeof router.currentRoute.value.query.redirect === 'string'
        ? router.currentRoute.value.query.redirect
        : '/summary'
    await router.replace(redirect)
  } catch (err) {
    error.value = parseApiError(err, t('auth.registrationFailed'))
  }
}
</script>

<template>
  <form class="stack" @submit.prevent="onSubmit" data-testid="register-form">
    <div>
      <h2>{{ t('auth.createYourAccount') }}</h2>
      <p class="muted">{{ t('auth.registerHint') }}</p>
    </div>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div class="stack">
      <label for="register-username">{{ t('auth.username') }}</label>
      <InputText
        id="register-username"
        v-model="form.username"
        autocomplete="username"
        data-testid="register-username"
      />
      <small v-if="fieldErrors.username" class="error">{{ fieldErrors.username }}</small>
    </div>

    <div class="stack">
      <label for="register-email">{{ t('auth.email') }}</label>
      <InputText
        id="register-email"
        v-model="form.email"
        type="email"
        autocomplete="email"
        data-testid="register-email"
      />
      <small v-if="fieldErrors.email" class="error">{{ fieldErrors.email }}</small>
    </div>

    <div class="stack">
      <label for="register-password">{{ t('auth.password') }}</label>
      <Password
        input-id="register-password"
        v-model="form.password"
        :feedback="false"
        toggle-mask
        autocomplete="new-password"
        class="w-full"
        input-class="w-full"
      />
      <small v-if="fieldErrors.password" class="error">{{ fieldErrors.password }}</small>
    </div>

    <Button
      type="submit"
      :label="t('auth.register')"
      :loading="auth.loading"
      :disabled="!canSubmit"
      data-testid="register-submit"
    />

    <div class="links">
      <RouterLink :to="{ name: 'login' }" class="auth-link flex-center">
        <i class="pi pi-user" style="margin-right: 0.4rem; color: var(--bv-primary)"></i>
        {{ t('auth.alreadyHaveAccount') }}
      </RouterLink>
    </div>

    <div class="divider">
      <span class="circle"></span>
    </div>

    <div class="bottom-links">
      <RouterLink class="demo-link flex-center" :to="{ name: 'plans' }" data-testid="register-plans-link">
        {{ t('nav.plans') }} <i class="pi pi-chevron-right" style="font-size: 0.75rem; margin-left: 0.4rem"></i>
      </RouterLink>
      <RouterLink class="demo-link flex-center" :to="{ name: 'comparar' }" data-testid="register-demo-link">
        {{ t('demo.badge') }} <i class="pi pi-chevron-right" style="font-size: 0.75rem; margin-left: 0.4rem"></i>
      </RouterLink>
    </div>
  </form>
</template>

<style scoped>
.links {
  display: flex;
  justify-content: center;
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

:deep(.p-password),
:deep(.p-password-input) {
  width: 100%;
}
</style>
