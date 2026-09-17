<template>
  <div class="progress-bar-container">
    <div class="progress-bar-track">
      <div 
        class="progress-bar-fill" 
        :style="{ width: `${clampedProgress}%` }"
        :class="{
          'is-complete': isComplete,
          'is-error': isError,
          'is-active': isActive
        }"
      ></div>
    </div>
    <div class="progress-bar-labels" v-if="showLabels">
      <span class="progress-stage">{{ stageText }}</span>
      <span class="progress-percent">{{ Math.round(clampedProgress) }}%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  progress: number
  stage?: string | null
  status?: string | null
  showLabels?: boolean
}>()

const { t } = useI18n()

const clampedProgress = computed(() => Math.min(100, Math.max(0, props.progress || 0)))
const isComplete = computed(() => props.status === 'COMPLETED' || clampedProgress.value >= 100)
const isError = computed(() => props.status === 'FAILED')
const isActive = computed(() => !isComplete.value && !isError.value && props.status === 'PROCESSING')

const stageText = computed(() => {
  if (isError.value) return t('job.status.failed')
  if (isComplete.value) return t('job.status.completed')
  if (props.stage) return t(`job.phase.${props.stage.toLowerCase()}`, props.stage)
  return t('job.status.processing')
})
</script>

<style scoped>
.progress-bar-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.progress-bar-track {
  width: 100%;
  height: 6px;
  background-color: var(--p-surface-200);
  border-radius: 4px;
  overflow: hidden;
}

.dark .progress-bar-track {
  background-color: var(--p-surface-700);
}

.progress-bar-fill {
  height: 100%;
  background-color: var(--p-primary-500);
  border-radius: 4px;
  transition: width 0.3s ease-in-out;
}

.progress-bar-fill.is-active {
  background: linear-gradient(90deg, var(--p-primary-400), var(--p-primary-600));
  background-size: 200% 100%;
  animation: progress-pulse 2s infinite ease-in-out;
}

.progress-bar-fill.is-complete {
  background-color: var(--p-green-500);
}

.progress-bar-fill.is-error {
  background-color: var(--p-red-500);
}

.progress-bar-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
  color: var(--p-text-color-secondary);
}

.progress-stage {
  font-weight: 500;
  text-transform: capitalize;
}

.progress-percent {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

@keyframes progress-pulse {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
</style>
