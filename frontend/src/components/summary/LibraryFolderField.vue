<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import { useLibraryStore } from '@/stores/library.store'
import type { SummaryDestination } from '@/types/brevio'
import { parseApiError } from '@/utils/errors'

const destination = defineModel<SummaryDestination>({ required: true })
const library = useLibraryStore()
const { t } = useI18n()
const mode = ref<'none' | 'existing' | 'new'>('none')
const loadError = ref<string | null>(null)

const modeOptions = computed(() => [
  { label: t('params.noFolder'), value: 'none' as const },
  { label: t('params.existingFolder'), value: 'existing' as const },
  { label: t('params.newFolder'), value: 'new' as const },
])

const folderOptions = computed(() =>
  library.folders.map((folder) => ({
    label: folder.name,
    value: folder.id,
  })),
)

function syncDestination() {
  if (mode.value === 'none') {
    destination.value = { library_folder_id: null, folder_name: null }
    return
  }
  if (mode.value === 'existing') {
    destination.value = {
      library_folder_id: destination.value.library_folder_id || null,
      folder_name: null,
    }
    return
  }
  destination.value = {
    library_folder_id: null,
    folder_name: destination.value.folder_name || '',
  }
}

watch(mode, syncDestination)

onMounted(async () => {
  try {
    await library.load()
  } catch (err) {
    loadError.value = parseApiError(err)
  }
  if (destination.value.folder_name) mode.value = 'new'
  else if (destination.value.library_folder_id) mode.value = 'existing'
})
</script>

<template>
  <div class="folder-field" data-testid="summary-folder-field">
    <div class="stack">
      <label for="param-folder-mode">{{ t('params.folder') }}</label>
      <Select
        input-id="param-folder-mode"
        v-model="mode"
        :options="modeOptions"
        option-label="label"
        option-value="value"
        class="w-full"
        data-testid="summary-folder-mode"
      />
      <p class="hint">{{ t('params.folderHint') }}</p>
    </div>
    <div v-if="mode === 'existing'" class="stack">
      <label for="param-folder">{{ t('params.selectFolder') }}</label>
      <Select
        input-id="param-folder"
        v-model="destination.library_folder_id"
        :options="folderOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('params.selectFolder')"
        class="w-full"
        data-testid="summary-folder-select"
      />
      <p v-if="loadError" class="hint hint-warn">{{ loadError }}</p>
    </div>
    <div v-else-if="mode === 'new'" class="stack">
      <label for="param-folder-name">{{ t('params.newFolderName') }}</label>
      <InputText
        id="param-folder-name"
        v-model="destination.folder_name"
        :placeholder="t('store.newFolderPlaceholder')"
        class="w-full"
        data-testid="summary-folder-name"
      />
    </div>
  </div>
</template>

<style scoped>
.folder-field {
  display: grid;
  gap: 0.75rem;
}

.hint {
  margin: 0.35rem 0 0;
  font-size: 0.8rem;
  color: #64748b;
}

.hint-warn {
  color: #b45309;
}
</style>
