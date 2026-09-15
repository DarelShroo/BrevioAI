<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import FileUpload, { type FileUploadSelectEvent } from 'primevue/fileupload'
import Message from 'primevue/message'

const props = withDefaults(
  defineProps<{
    accept: string
    hint: string
    multiple?: boolean
    validator: (file: File) => boolean
    invalidMessage: string
  }>(),
  {
    multiple: true,
  },
)

const { t } = useI18n()
const files = defineModel<File[]>('files', { default: () => [] })
const localError = ref<string | null>(null)

const allowMultiple = computed(() => props.multiple)
const fileCount = computed(() => files.value.length)

function fileKey(file: File): string {
  return `${file.name}::${file.size}::${file.lastModified}`
}

function onSelect(event: FileUploadSelectEvent) {
  localError.value = null
  const raw = Array.from(event.files ?? [])
  const selected: File[] = raw.filter((file): file is File => file instanceof File)
  const invalid = selected.filter((file) => !props.validator(file))
  if (invalid.length) {
    localError.value = props.invalidMessage
    return
  }
  if (!allowMultiple.value) {
    files.value = selected.slice(0, 1)
    return
  }

  const next = [...files.value]
  const seen = new Set(next.map(fileKey))
  for (const file of selected) {
    const key = fileKey(file)
    if (seen.has(key)) continue
    seen.add(key)
    next.push(file)
  }
  files.value = next
}

function removeAt(index: number) {
  files.value = files.value.filter((_, i) => i !== index)
  localError.value = null
}

function clear() {
  files.value = []
  localError.value = null
}
</script>

<template>
  <div class="stack file-picker" data-testid="file-picker">
    <div class="row picker-actions">
      <FileUpload
        mode="basic"
        :multiple="allowMultiple"
        :choose-label="allowMultiple ? t('files.choose') : t('files.chooseOne')"
        custom-upload
        auto
        data-testid="file-picker-input"
        :data-accept="accept"
        @select="onSelect"
      />
      <span v-if="fileCount" class="count" data-testid="file-picker-count">
        {{ t('files.count', { n: fileCount }, fileCount) }}
      </span>
    </div>
    <p class="muted">{{ hint }}</p>
    <div v-if="localError" data-testid="file-picker-error">
      <Message severity="error" :closable="false">{{ localError }}</Message>
    </div>
    <ul v-if="fileCount" class="file-list" data-testid="file-picker-list">
      <li v-for="(file, index) in files" :key="fileKey(file)" class="file-item">
        <span class="file-name" :title="file.name">{{ file.name }}</span>
        <Button
          :label="t('files.remove')"
          severity="secondary"
          text
          size="small"
          :aria-label="t('files.removeNamed', { name: file.name })"
          data-testid="file-picker-remove"
          @click="removeAt(index)"
        />
      </li>
    </ul>
    <div v-if="fileCount" class="row">
      <Button
        :label="t('files.clear')"
        severity="secondary"
        text
        size="small"
        data-testid="file-picker-clear"
        @click="clear"
      />
    </div>
  </div>
</template>

<style scoped>
.picker-actions {
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.count {
  font-size: 0.8rem;
  font-weight: 650;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 999px;
  padding: 0.2rem 0.65rem;
}

.file-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.55rem 0.75rem;
  background: var(--bv-bg-muted);
  border: 1px solid var(--bv-border);
  border-radius: var(--bv-radius-sm);
}

.file-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--bv-ink);
}
</style>
