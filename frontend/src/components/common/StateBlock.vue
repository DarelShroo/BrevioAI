<script setup lang="ts">
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import { useI18n } from 'vue-i18n'

defineProps<{
  loading?: boolean
  error?: string | null
  empty?: boolean
  emptyTitle?: string
  emptyMessage?: string
  retryLabel?: string
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n()
</script>

<template>
  <div class="state-block">
    <div v-if="loading" class="center" role="status" aria-live="polite" data-testid="state-loading">
      <ProgressSpinner style="width: 42px; height: 42px" strokeWidth="4" />
      <p class="muted">{{ t('common.loading') }}</p>
    </div>

    <div v-else-if="error" class="error-box card-surface" data-testid="state-error">
      <Message severity="error" :closable="false">{{ error }}</Message>
      <Button
        :label="retryLabel || t('common.retry')"
        icon="pi pi-refresh"
        severity="secondary"
        @click="emit('retry')"
      />
    </div>

    <div v-else-if="empty" class="empty card-surface" role="status" data-testid="state-empty">
      <slot name="empty">
        <i class="pi pi-inbox empty-icon" aria-hidden="true" />
        <h3>{{ emptyTitle || t('common.emptyTitle') }}</h3>
        <p class="muted">{{ emptyMessage || t('common.emptyMessage') }}</p>
      </slot>
    </div>

    <slot v-else />
  </div>
</template>

<style scoped>
.center {
  display: grid;
  place-items: center;
  gap: var(--bv-space-3);
  padding: var(--bv-space-6);
}

.empty {
  padding: var(--bv-space-7) var(--bv-space-5);
  text-align: center;
  display: grid;
  justify-items: center;
  gap: var(--bv-space-3);
}

.empty-icon {
  font-size: 2rem;
  color: var(--bv-primary);
  background: var(--bv-primary-soft);
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 999px;
  display: grid;
  place-items: center;
}

.error-box {
  padding: var(--bv-space-5);
  display: grid;
  gap: var(--bv-space-3);
  justify-items: start;
}
</style>
