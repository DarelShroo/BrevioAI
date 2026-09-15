<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Password from 'primevue/password'
import Message from 'primevue/message'
import * as authService from '@/services/auth.service'
import { parseApiError } from '@/utils/errors'
import { isValidEmail, validatePassword } from '@/utils/validation'

const { t } = useI18n()
const step = ref<'handshake' | 'verify'>('handshake')
const loading = ref(false)
const message = ref<string | null>(null)
const error = ref<string | null>(null)

const handshake = reactive({ identity: '' })
const verify = reactive({
  email: '',
  password: '',
  otp: null as number | null,
})

async function sendOtp() {
  error.value = null
  message.value = null
  if (!isValidEmail(handshake.identity)) {
    error.value = t('validation.validEmailAddress')
    return
  }
  loading.value = true
  try {
    const data = await authService.passwordRecoveryHandshake({
      identity: handshake.identity.trim(),
    })
    verify.email = handshake.identity.trim()
    message.value = data.message || t('auth.otpSent')
    step.value = 'verify'
  } catch (err) {
    error.value = parseApiError(err)
  } finally {
    loading.value = false
  }
}

async function verifyOtp() {
  error.value = null
  message.value = null
  const passwordError = validatePassword(verify.password)
  if (!isValidEmail(verify.email) || passwordError || verify.otp == null) {
    error.value = passwordError || t('validation.recoveryFields')
    return
  }
  loading.value = true
  try {
    const data = await authService.passwordRecoveryVerify({
      email: verify.email.trim(),
      password: verify.password,
      otp: Number(verify.otp),
    })
    message.value = data.message || t('auth.passwordUpdated')
  } catch (err) {
    error.value = parseApiError(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="stack" data-testid="password-recovery">
    <div>
      <h2>{{ t('auth.passwordRecovery') }}</h2>
      <p class="muted">{{ t('auth.recoveryHint') }}</p>
    </div>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Message v-if="message" severity="success" :closable="false">{{ message }}</Message>

    <form v-if="step === 'handshake'" class="stack" @submit.prevent="sendOtp">
      <label for="recovery-email">{{ t('auth.email') }}</label>
      <InputText id="recovery-email" v-model="handshake.identity" type="email" />
      <Button type="submit" :label="t('auth.sendOtp')" :loading="loading" />
    </form>

    <form v-else class="stack" @submit.prevent="verifyOtp">
      <label for="verify-email">{{ t('auth.email') }}</label>
      <InputText id="verify-email" v-model="verify.email" type="email" />

      <label for="verify-otp">{{ t('auth.otp') }}</label>
      <InputNumber id="verify-otp" v-model="verify.otp" :use-grouping="false" class="w-full" />

      <label for="verify-password">{{ t('auth.newPassword') }}</label>
      <Password
        input-id="verify-password"
        v-model="verify.password"
        toggle-mask
        class="w-full"
        input-class="w-full"
      />

      <Button type="submit" :label="t('auth.updatePassword')" :loading="loading" />
    </form>

    <RouterLink :to="{ name: 'login' }">{{ t('auth.backToSignIn') }}</RouterLink>
  </div>
</template>

<style scoped>
.w-full {
  width: 100%;
}

:deep(.p-password),
:deep(.p-password-input),
:deep(.p-inputnumber),
:deep(.p-inputnumber-input) {
  width: 100%;
}
</style>
