<script setup lang="ts">
import type { EstimateDocumentsData } from '@/types/brevio'
import Message from 'primevue/message'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { isLocalModelId } from '@/utils/models'

const props = defineProps<{
  estimate: EstimateDocumentsData | null
}>()

const { t } = useI18n()

const isLocalEstimate = computed(() => {
  if (!props.estimate) return false
  return (
    props.estimate.model.access === 'local' ||
    props.estimate.credits.expected === 0 ||
    isLocalModelId(props.estimate.model.name, props.estimate.model.provider)
  )
})
</script>

<template>
  <div v-if="estimate" class="estimate card-surface" data-testid="estimate-panel">
    <div class="row head">
      <h3>{{ t('estimate.title') }}</h3>
      <Message :severity="estimate.can_process ? 'success' : 'warn'" :closable="false">
        {{ estimate.can_process ? t('estimate.ready') : estimate.reason || t('estimate.cannotProcess') }}
      </Message>
    </div>
    <div class="grid">
      <div>
        <span class="muted">{{ t('estimate.inputTokens') }}</span>
        <strong>{{ estimate.estimation.input_tokens.total }}</strong>
      </div>
      <div>
        <span class="muted">{{ t('estimate.expectedOutput') }}</span>
        <strong>{{ estimate.estimation.output_tokens.expected }}</strong>
      </div>
      <div>
        <span class="muted">{{ t('estimate.credits') }}</span>
        <strong v-if="isLocalEstimate">
          {{ t('estimate.localFree') }}
        </strong>
        <strong v-else>{{ estimate.credits.expected }}–{{ estimate.credits.maximum }}</strong>
      </div>
      <div>
        <span class="muted">{{ t('estimate.platformCost') }}</span>
        <strong>
          {{ estimate.pricing.expected_cost.toFixed(4) }}
          {{ estimate.pricing.platform_currency }}
        </strong>
      </div>
    </div>
    <div v-if="estimate.documents?.length" class="docs" data-testid="estimate-documents">
      <h4>{{ t('estimate.documents') }}</h4>
      <ul>
        <li v-for="doc in estimate.documents" :key="doc.filename">
          <strong>{{ doc.filename }}</strong>
          <span class="muted">
            · {{ t('estimate.documentTokens', { n: doc.tokens }) }}
            · {{ doc.extraction.status }}
          </span>
        </li>
      </ul>
    </div>
    <ul v-if="estimate.warnings?.length" class="warnings">
      <li v-for="warning in estimate.warnings" :key="warning.code">
        {{ warning.message }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.estimate {
  padding: var(--bv-space-4);
}

.head {
  justify-content: space-between;
  margin-bottom: var(--bv-space-3);
  flex-wrap: wrap;
}

.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--bv-space-3);
}

.docs {
  margin-top: var(--bv-space-4);
}

.docs h4 {
  margin: 0 0 var(--bv-space-2);
  font-size: 0.85rem;
}

.docs ul {
  margin: 0;
  padding-left: 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.docs li {
  font-size: 0.85rem;
}

.grid span {
  display: block;
  font-size: 0.85rem;
}

.warnings {
  margin: var(--bv-space-3) 0 0;
  padding-left: 1.1rem;
  color: var(--bv-warning);
}

@media (max-width: 768px) {
  .grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
