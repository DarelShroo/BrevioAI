<script setup lang="ts">
import { Calendar, Download, Eye, FileCheck, FileText, Folder, Trash2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { FolderEntry } from '@/types/user'
import {
  entryPrimaryName,
  entryResultCount,
  entrySourceLabel,
  entryStatus,
  formatEntryDate,
} from '@/utils/entries'

defineProps<{
  entry: FolderEntry
  selected?: boolean
  canDownload?: boolean
}>()

const emit = defineEmits<{
  open: []
  download: []
  delete: []
  toggleSelect: []
}>()

const { t } = useI18n()
</script>

<template>
  <article class="entry-card" :class="{ selected }" data-testid="store-entry-card">
    <div>
      <div class="top">
        <div class="lead">
          <label class="check">
            <input
              type="checkbox"
              :checked="selected"
              data-testid="store-entry-select"
              :aria-label="entryPrimaryName(entry)"
              @click.stop
              @change="emit('toggleSelect')"
            />
          </label>
          <span class="type-icon" :aria-label="entrySourceLabel(entry)">
            <FileText :size="18" :stroke-width="2" aria-hidden="true" />
          </span>
        </div>
        <StatusBadge :status="entryStatus(entry)" />
      </div>

      <h3 class="title font-serif">{{ entryPrimaryName(entry) }}</h3>

      <div class="meta">
        <p>
          <span>
            <FileCheck :size="13" :stroke-width="2" aria-hidden="true" />
            {{ t('store.resultCount', { n: entryResultCount(entry) }, entryResultCount(entry)) }}
          </span>
          <span class="dot" aria-hidden="true">•</span>
          <span>
            <Folder :size="13" :stroke-width="2" aria-hidden="true" />
            {{ entrySourceLabel(entry) }}
          </span>
        </p>
        <p v-if="formatEntryDate(entry)">
          <span>
            <Calendar :size="13" :stroke-width="2" aria-hidden="true" />
            {{ formatEntryDate(entry) }}
          </span>
        </p>
      </div>
    </div>

    <div class="actions">
      <div class="primary">
        <button type="button" class="text-btn" data-testid="store-view-btn" @click="emit('open')">
          <Eye :size="14" :stroke-width="2" />
          <span>{{ t('store.open') }}</span>
        </button>
        <button
          v-if="canDownload"
          type="button"
          class="text-btn"
          data-testid="store-download-btn"
          :aria-label="t('store.download')"
          @click="emit('download')"
        >
          <Download :size="14" :stroke-width="2" />
          <span>{{ t('store.download') }}</span>
        </button>
      </div>
      <button
        type="button"
        class="icon-danger"
        :aria-label="t('store.deleteEntry')"
        data-testid="store-delete-btn"
        @click="emit('delete')"
      >
        <Trash2 :size="15" :stroke-width="2" />
      </button>
    </div>
  </article>
</template>

<style scoped>
.entry-card {
  background: #fff;
  border: 1px solid rgb(226 232 240 / 0.7);
  border-radius: 1rem;
  padding: 1.25rem;
  box-shadow: 0 1px 2px rgb(15 23 42 / 0.04);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 11.5rem;
  transition:
    box-shadow 0.15s ease,
    border-color 0.15s ease;
}

.entry-card:hover {
  box-shadow: 0 8px 20px rgb(15 23 42 / 0.08);
  border-color: #99f6e4;
}

.entry-card.selected {
  border-color: #14b8a6;
  box-shadow: 0 0 0 1px #14b8a6;
}

.lead {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.check input {
  width: 1rem;
  height: 1rem;
  accent-color: #0f766e;
}

.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.type-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: #f0fdfa;
  color: #0d9488;
}

.title {
  margin: 0.75rem 0 0;
  font-family: var(--bv-font-serif);
  font-optical-sizing: auto;
  font-size: 0.875rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #64748b;
}

.meta p {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.45rem;
  margin: 0 0 0.25rem;
  color: inherit;
}

.meta span {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.dot {
  color: #94a3b8;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid #f1f5f9;
  font-size: 0.75rem;
}

.primary {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.text-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border: 0;
  background: transparent;
  color: #0f766e;
  font: inherit;
  font-weight: 500;
  padding: 0;
  cursor: pointer;
}

.text-btn:hover:not(:disabled) {
  color: #134e4a;
}

.text-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.icon-danger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: 0;
  background: transparent;
  color: #f43f5e;
  border-radius: 0.375rem;
  cursor: pointer;
}

.icon-danger:hover {
  color: #be123c;
  background: #fff1f2;
}
</style>
