<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { StoreCountSummary } from '@/components/store/types'

defineProps<{
  counts: StoreCountSummary
}>()

const { t } = useI18n()
</script>

<template>
  <div class="metrics">
    <span class="pill pill-neutral font-sans">{{ t('store.total', { n: counts.ALL }) }}</span>
    <span class="pill pill-amber">{{ t('store.processing', { n: counts.PROCESSING }) }}</span>
    <span class="pill pill-emerald">{{ t('store.completed', { n: counts.COMPLETED }) }}</span>
    <span class="pill pill-rose">{{ t('store.failed', { n: counts.FAILED }) }}</span>
  </div>
</template>

<style scoped>
.metrics {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1rem;
  font-family: var(--bv-font-sans);
  font-size: 0.75rem;
  font-weight: 500;
}

.pill {
  border-radius: 999px;
  padding: 0.25rem 0.75rem;
  border: 1px solid transparent;
}

.pill-neutral {
  background: #f1f5f9;
  color: #334155;
  border-color: #e2e8f0;
}

.pill-amber {
  background: #fffbeb;
  color: #92400e;
  border-color: #fde68a;
}

.pill-emerald {
  background: #ecfdf5;
  color: #065f46;
  border-color: #a7f3d0;
}

.pill-rose {
  background: #fff1f2;
  color: #be123c;
  border-color: #fecdd3;
}
</style>
