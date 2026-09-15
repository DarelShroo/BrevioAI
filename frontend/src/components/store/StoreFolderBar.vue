<script setup lang="ts">
import { Folder, FolderOpen, Inbox, Pencil, Plus, Trash2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import type { LibraryFolder } from '@/types/user'

const props = defineProps<{
  folders: LibraryFolder[]
  unfiledCount: number
  currentScope: 'all' | 'unfiled' | string
}>()

const emit = defineEmits<{
  select: [scope: 'all' | 'unfiled' | string]
  create: []
  rename: [folder: LibraryFolder]
  remove: [folder: LibraryFolder]
}>()

const { t } = useI18n()

function isActive(scope: string) {
  return props.currentScope === scope
}

function currentFolder() {
  return props.folders.find((item) => item.id === props.currentScope) || null
}
</script>

<template>
  <section class="folder-bar" data-testid="store-folder-bar">
    <div class="chips">
      <button
        type="button"
        class="chip"
        :class="{ active: isActive('all') }"
        data-testid="store-scope-all"
        @click="emit('select', 'all')"
      >
        <FolderOpen :size="14" :stroke-width="2" />
        <span>{{ t('store.allSummaries') }}</span>
      </button>
      <button
        type="button"
        class="chip"
        :class="{ active: isActive('unfiled') }"
        data-testid="store-scope-unfiled"
        @click="emit('select', 'unfiled')"
      >
        <Inbox :size="14" :stroke-width="2" />
        <span>{{ t('store.unfiled') }}</span>
        <em>{{ unfiledCount }}</em>
      </button>
      <button
        v-for="folder in folders"
        :key="folder.id"
        type="button"
        class="chip folder"
        :class="{ active: isActive(folder.id) }"
        :data-testid="`store-scope-folder-${folder.id}`"
        @click="emit('select', folder.id)"
      >
        <Folder :size="14" :stroke-width="2" />
        <span class="name">{{ folder.name }}</span>
        <em>{{ folder.entry_count }}</em>
      </button>
    </div>
    <div class="actions">
      <button
        v-if="currentFolder()"
        type="button"
        class="icon-btn"
        :aria-label="t('store.renameFolder')"
        data-testid="store-rename-folder"
        @click="emit('rename', currentFolder()!)"
      >
        <Pencil :size="14" :stroke-width="2" />
      </button>
      <button
        v-if="currentFolder()"
        type="button"
        class="icon-btn danger"
        :aria-label="t('store.deleteFolder')"
        data-testid="store-delete-folder"
        @click="emit('remove', currentFolder()!)"
      >
        <Trash2 :size="14" :stroke-width="2" />
      </button>
      <button
        type="button"
        class="create"
        data-testid="store-create-folder"
        @click="emit('create')"
      >
        <Plus :size="14" :stroke-width="2" />
        <span>{{ t('store.createFolder') }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.folder-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin: 0 0 1rem;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  min-width: 0;
}

.chip,
.create,
.icon-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #334155;
  border-radius: 999px;
  padding: 0.4rem 0.75rem;
  font: inherit;
  font-size: 0.8rem;
  cursor: pointer;
}

.chip .name {
  max-width: 10rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip em {
  font-style: normal;
  color: #64748b;
  font-size: 0.75rem;
}

.chip.active,
.create:hover,
.chip:hover {
  border-color: #99f6e4;
  background: #f0fdfa;
  color: #0f766e;
}

.create {
  color: #0f766e;
  font-weight: 600;
}

.actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.icon-btn {
  width: 2rem;
  height: 2rem;
  padding: 0;
  justify-content: center;
  border-radius: 0.5rem;
}

.icon-btn.danger {
  color: #f43f5e;
}

.icon-btn.danger:hover {
  background: #fff1f2;
  border-color: #fecdd3;
}
</style>
