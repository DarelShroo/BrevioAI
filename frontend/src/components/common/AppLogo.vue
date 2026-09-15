<script setup lang="ts">
import logoUrl from '@/assets/images/brevio_logo.png'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

withDefaults(
  defineProps<{
    size?: 'sm' | 'md' | 'lg'
    showWordmark?: boolean
    compact?: boolean
    inverted?: boolean
  }>(),
  {
    size: 'md',
    showWordmark: true,
    compact: false,
    inverted: false,
  },
)
</script>

<template>
  <div class="app-logo" :class="[`size-${size}`, { compact, inverted }]">
    <img :src="logoUrl" :alt="t('app.name')" class="mark" width="96" height="96" />
    <div v-if="showWordmark" class="wordmark">
      <strong>{{ t('app.name') }}</strong>
      <span v-if="!compact" class="tagline">{{ t('app.tagline') }}</span>
    </div>
  </div>
</template>

<style scoped>
.app-logo {
  display: flex;
  align-items: center;
  gap: var(--bv-space-3);
  min-width: 0;
}

.mark {
  display: block;
  object-fit: contain;
  border-radius: 12px;
  background: transparent;
}

.size-sm .mark {
  width: 2rem;
  height: 2rem;
}

.size-md .mark {
  width: 2.75rem;
  height: 2.75rem;
}

.size-lg .mark {
  width: 4.5rem;
  height: 4.5rem;
}

.wordmark {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.wordmark strong {
  font-family: var(--bv-font-serif);
  font-optical-sizing: auto;
  font-size: 1.15rem;
  line-height: 1.1;
  color: inherit;
}

.tagline {
  color: inherit;
  opacity: 0.72;
  font-size: 0.8rem;
}

.compact .wordmark strong {
  font-size: 1rem;
}

.inverted {
  color: #fff;
}

.inverted .wordmark strong {
  font-weight: 600;
  letter-spacing: -0.02em;
}

.inverted .tagline {
  color: #d7eeea;
  opacity: 0.86;
}
</style>
