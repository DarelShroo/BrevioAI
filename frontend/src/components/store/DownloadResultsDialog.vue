<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import { formatLabel } from '@/utils/labels'
import type { DownloadFormat } from '@/types/brevio'
import type { FolderEntry } from '@/types/user'
import { completedDownloadableResults, entryPrimaryName } from '@/utils/entries'

const props = defineProps<{
  visible: boolean
  entry: FolderEntry | null
  preferredIndex?: number | null
  initialFormat?: DownloadFormat
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  confirm: [payload: { indexes: number[]; format: DownloadFormat }]
}>()

const { t, te } = useI18n()
const format = ref<DownloadFormat>('md')
const selected = ref<number[]>([])

const formatOptions = computed(() =>
  ['md', 'docx', 'pdf', 'txt'].map((id) => ({
    label: formatLabel(id, t, te),
    value: id as DownloadFormat,
  })),
)

const options = computed(() =>
  props.entry ? completedDownloadableResults(props.entry) : [],
)

const allSelected = computed({
  get: () => options.value.length > 0 && selected.value.length === options.value.length,
  set: (value: boolean) => {
    selected.value = value ? options.value.map((item) => item.index) : []
  },
})

const canConfirm = computed(() => selected.value.length > 0 && !props.loading)

watch(
  () => [props.visible, props.entry, props.preferredIndex, props.initialFormat] as const,
  ([visible]) => {
    if (!visible || !props.entry) return
    format.value = props.initialFormat || 'md'
    const items = completedDownloadableResults(props.entry)
    if (!items.length) {
      selected.value = []
      return
    }
    const preferred =
      typeof props.preferredIndex === 'number'
        ? items.find((item) => item.index === props.preferredIndex)
        : null
    selected.value = preferred ? [preferred.index] : items.map((item) => item.index)
  },
  { immediate: true },
)

function close() {
  emit('update:visible', false)
}

function confirm() {
  if (!canConfirm.value) return
  emit('confirm', { indexes: [...selected.value], format: format.value })
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :header="t('store.downloadDialogTitle')"
    :style="{ width: 'min(28rem, 92vw)' }"
    data-testid="store-download-dialog"
    @update:visible="emit('update:visible', $event)"
  >
    <div v-if="entry" class="stack dialog-body">
      <p class="muted tiny">
        {{ t('store.downloadDialogHint', { name: entryPrimaryName(entry) }) }}
      </p>

      <div v-if="options.length" class="result-picker" data-testid="store-download-options">
        <label v-if="options.length > 1" class="pick-all">
          <Checkbox v-model="allSelected" binary data-testid="store-download-all" />
          <span>{{ t('store.downloadSelectAll') }}</span>
        </label>
        <label
          v-for="item in options"
          :key="item.index"
          class="pick-row"
          :data-testid="`store-download-option-${item.index}`"
        >
          <Checkbox v-model="selected" :value="item.index" />
          <span class="pick-name" :title="item.name">{{ item.name }}</span>
        </label>
      </div>
      <p v-else class="muted">{{ t('store.downloadNoneReady') }}</p>

      <label for="store-dl-format">{{ t('store.format') }}</label>
      <Select
        input-id="store-dl-format"
        v-model="format"
        :options="formatOptions"
        option-label="label"
        option-value="value"
        class="w-full"
        data-testid="store-download-format"
      />

      <div class="row actions">
        <Button :label="t('common.cancel')" text :disabled="loading" @click="close" />
        <Button
          :label="t('store.downloadSelected', { n: selected.length }, selected.length)"
          icon="pi pi-download"
          :loading="loading"
          :disabled="!canConfirm"
          data-testid="store-download-confirm"
          @click="confirm"
        />
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.dialog-body {
  gap: 0.85rem;
}

.tiny {
  font-size: 0.85rem;
  margin: 0;
}

.result-picker {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  max-height: 14rem;
  overflow: auto;
  padding: 0.65rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  background: #f8fafc;
}

.pick-all,
.pick-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin: 0;
  cursor: pointer;
  font-size: 0.9rem;
  color: #0f172a;
}

.pick-all {
  font-weight: 650;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid #e2e8f0;
}

.pick-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions {
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>
