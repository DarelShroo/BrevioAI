<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, RefreshCw, Search } from '@lucide/vue'
import type {
  StoreSelectOption,
  StoreSortField,
  StoreStatusFilter,
  StoreViewMode,
} from '@/components/store/types'

const filter = defineModel<string>('filter', { required: true })
const statusFilter = defineModel<StoreStatusFilter>('statusFilter', { required: true })
const sortField = defineModel<StoreSortField>('sortField', { required: true })
const viewMode = defineModel<StoreViewMode>('viewMode', { required: true })

defineProps<{
  loading?: boolean
  statusOptions: StoreSelectOption<StoreStatusFilter>[]
  sortOptions: StoreSelectOption<StoreSortField>[]
  viewOptions: StoreSelectOption<StoreViewMode>[]
}>()

const emit = defineEmits<{
  refresh: []
}>()

const { t } = useI18n()
const filtersOpen = ref(false)
const sortOpen = ref(false)
const filtersRoot = ref<HTMLElement | null>(null)
const sortRoot = ref<HTMLElement | null>(null)

function closeMenus() {
  filtersOpen.value = false
  sortOpen.value = false
}

function onDocumentClick(event: MouseEvent) {
  const target = event.target as Node | null
  if (!target) return
  if (filtersOpen.value && !filtersRoot.value?.contains(target)) filtersOpen.value = false
  if (sortOpen.value && !sortRoot.value?.contains(target)) sortOpen.value = false
}

function onEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') closeMenus()
}

function chooseStatus(value: StoreStatusFilter) {
  statusFilter.value = value
  filtersOpen.value = false
}

function chooseSort(value: StoreSortField) {
  sortField.value = value
  sortOpen.value = false
}

function chooseView(value: StoreViewMode) {
  viewMode.value = value
  filtersOpen.value = false
}

onMounted(() => {
  document.addEventListener('mousedown', onDocumentClick)
  document.addEventListener('keydown', onEscape)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onDocumentClick)
  document.removeEventListener('keydown', onEscape)
})
</script>

<template>
  <section class="toolbar">
    <label class="search">
      <Search :size="16" :stroke-width="2" class="search-icon" aria-hidden="true" />
      <input
        v-model="filter"
        type="search"
        :placeholder="t('store.searchPlaceholder')"
        :aria-label="t('store.searchAria')"
        data-testid="store-filter"
      />
    </label>

    <div class="actions">
      <div ref="filtersRoot" class="menu-wrap">
        <button
          type="button"
          class="toolbar-btn"
          :aria-expanded="filtersOpen"
          aria-haspopup="menu"
          data-testid="store-status-filter"
          @click="
            () => {
              filtersOpen = !filtersOpen
              sortOpen = false
            }
          "
        >
          <span>{{ t('store.advancedFilters') }}</span>
          <ChevronDown :size="16" :stroke-width="2" />
        </button>
        <div v-if="filtersOpen" class="menu" role="menu">
          <p class="menu-label">{{ t('store.filterStatus') }}</p>
          <button
            v-for="option in statusOptions"
            :key="option.value"
            type="button"
            role="menuitemradio"
            :aria-checked="statusFilter === option.value"
            :class="{ selected: statusFilter === option.value }"
            @click="chooseStatus(option.value)"
          >
            {{ option.label }}
          </button>
          <p class="menu-label">{{ t('store.viewMode') }}</p>
          <div class="view-row" data-testid="store-view-mode">
            <button
              v-for="option in viewOptions"
              :key="option.value"
              type="button"
              :class="{ selected: viewMode === option.value }"
              @click="chooseView(option.value)"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
      </div>

      <div ref="sortRoot" class="menu-wrap">
        <button
          type="button"
          class="toolbar-btn"
          :aria-expanded="sortOpen"
          aria-haspopup="menu"
          :aria-label="t('store.sortEntries')"
          data-testid="store-sort"
          @click="
            () => {
              sortOpen = !sortOpen
              filtersOpen = false
            }
          "
        >
          <span>{{ t('store.sortBy') }}</span>
          <ChevronDown :size="16" :stroke-width="2" />
        </button>
        <div v-if="sortOpen" class="menu" role="menu">
          <button
            v-for="option in sortOptions"
            :key="option.value"
            type="button"
            role="menuitemradio"
            :aria-checked="sortField === option.value"
            :class="{ selected: sortField === option.value }"
            @click="chooseSort(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <button
        type="button"
        class="toolbar-btn refresh"
        :disabled="loading"
        @click="emit('refresh')"
      >
        <RefreshCw :size="16" :stroke-width="2" :class="{ spinning: loading }" />
        <span>{{ t('store.refresh') }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin: 0 0 1.5rem;
  padding: 0.75rem;
  background: #fff;
  border: 1px solid rgb(226 232 240 / 0.8);
  border-radius: 0.75rem;
  box-shadow: 0 1px 2px rgb(15 23 42 / 0.04);
}

.search {
  position: relative;
  display: flex;
  align-items: center;
  min-width: min(100%, 20rem);
  flex: 1 1 16rem;
}

.search-icon {
  position: absolute;
  inset-inline-start: 0.75rem;
  color: #94a3b8;
  pointer-events: none;
}

.search input {
  width: 100%;
  max-width: 20rem;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem 0.5rem 2.15rem;
  font: inherit;
  font-size: 0.875rem;
  color: #0f172a;
}

.search input:focus {
  outline: 2px solid #14b8a6;
  outline-offset: 1px;
  background: #fff;
  border-color: #99f6e4;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.menu-wrap {
  position: relative;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #334155;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  font: inherit;
  font-size: 0.875rem;
  cursor: pointer;
}

.toolbar-btn:hover,
.toolbar-btn[aria-expanded='true'] {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.toolbar-btn:disabled {
  opacity: 0.65;
  cursor: wait;
}

.refresh {
  color: #334155;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

.menu {
  position: absolute;
  top: calc(100% + 0.4rem);
  inset-inline-end: 0;
  min-width: 13rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  box-shadow: 0 12px 28px rgb(15 23 42 / 0.12);
  padding: 0.4rem;
  z-index: 20;
}

.menu-label {
  margin: 0.35rem 0.55rem 0.2rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}

.menu button {
  width: 100%;
  display: block;
  border: 0;
  background: transparent;
  color: #334155;
  text-align: start;
  font: inherit;
  font-size: 0.875rem;
  padding: 0.5rem 0.7rem;
  border-radius: 0.5rem;
  cursor: pointer;
}

.menu button:hover,
.menu button.selected {
  background: #f0fdfa;
  color: #0f766e;
}

.view-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.35rem;
  padding: 0.2rem 0.35rem 0.45rem;
}

.view-row button {
  text-align: center;
  border: 1px solid #e2e8f0;
  background: #fff;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 720px) {
  .search input {
    max-width: none;
  }
}
</style>
