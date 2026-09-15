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
      <RouterLink :to="{ name: 'register' }">{{ t('auth.createAccount') }}</RouterLink>
      <RouterLink :to="{ name: 'password-recovery' }">{{ t('auth.forgotPassword') }}</RouterLink>
    </div>
  </form>
</template>

<style scoped>
.links {
  display: flex;
  justify-content: space-between;
  gap: var(--bv-space-3);
  flex-wrap: wrap;
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
