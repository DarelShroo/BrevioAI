<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ChevronLeft, ChevronRight } from '@lucide/vue'

defineProps<{
  page: number
  totalPages: number
  count: number
}>()

const emit = defineEmits<{
  prev: []
  next: []
}>()

const { t } = useI18n()
</script>

<template>
  <nav class="pager" :aria-label="t('store.pager', { page: page + 1, total: totalPages, count })">
    <button
      type="button"
      class="page-btn"
      :disabled="page <= 0"
      :aria-label="t('store.previousPage')"
      @click="emit('prev')"
    >
      <ChevronLeft :size="16" :stroke-width="2" />
    </button>
    <span>
      {{ t('store.pager', { page: page + 1, total: totalPages, count }) }}
    </span>
    <button
      type="button"
      class="page-btn"
      :disabled="page >= totalPages - 1"
      :aria-label="t('store.nextPage')"
      @click="emit('next')"
    >
      <ChevronRight :size="16" :stroke-width="2" />
    </button>
  </nav>
</template>

<style scoped>
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem 0 0.5rem;
  font-size: 0.75rem;
  color: #64748b;
}

.page-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: 0;
  background: transparent;
  color: #64748b;
  border-radius: 0.5rem;
  cursor: pointer;
}

.page-btn:hover:not(:disabled) {
  background: #f1f5f9;
  color: #0f172a;
}

.page-btn:disabled {
  opacity: 0.35;
  cursor: default;
}
</style>
