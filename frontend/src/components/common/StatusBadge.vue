<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { statusLabel } from '@/utils/labels'

const props = defineProps<{
  status?: string | null
}>()

const { t, te } = useI18n()

const normalized = computed(() => String(props.status || 'UNKNOWN').toUpperCase())

const label = computed(() => statusLabel(normalized.value, t, te))

const tone = computed(() => {
  if (normalized.value === 'COMPLETED') return 'completed'
  if (normalized.value === 'FAILED') return 'failed'
  if (normalized.value === 'PROCESSING' || normalized.value === 'TRANSCRIBING' || normalized.value === 'TRANSCRIBED') {
    return 'processing'
  }
  return 'unknown'
})
</script>

<template>
  <span class="status-badge" :class="tone">{{ label }}</span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  width: max-content;
  font-weight: 600;
  font-size: 11px;
  line-height: 1.2;
  padding: 0.125rem 0.625rem;
  border-radius: 999px;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.completed {
  background: #ecfdf5;
  color: #047857;
}

.processing {
  background: #fffbeb;
  color: #b45309;
}

.failed {
  background: #fff1f2;
  color: #be123c;
}

.unknown {
  background: #f1f5f9;
  color: #475569;
}
</style>
