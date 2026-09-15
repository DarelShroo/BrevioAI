<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, LogOut, Settings } from '@lucide/vue'
import { useAuthStore } from '@/stores/auth.store'

const emit = defineEmits<{
  logout: []
}>()

const { t } = useI18n()
const auth = useAuthStore()
const open = ref(false)
const root = ref<HTMLElement | null>(null)

const username = computed(() => auth.profile?.username || t('app.name'))

const initials = computed(() => {
  const value = username.value.trim()
  const parts = value.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  }
  return value.slice(0, 2).toUpperCase() || 'B'
})

function toggle() {
  open.value = !open.value
}

function close() {
  open.value = false
}

function logout() {
  close()
  emit('logout')
}

function onDocumentClick(event: MouseEvent) {
  const target = event.target as Node | null
  if (open.value && target && !root.value?.contains(target)) {
    close()
  }
}

function onEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
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
  <div ref="root" class="user-menu">
    <button
      type="button"
      class="user-trigger"
      :aria-label="t('nav.userMenu')"
      :aria-expanded="open"
      aria-haspopup="menu"
      data-testid="user-menu"
      @click="toggle"
    >
      <span class="avatar" aria-hidden="true">{{ initials }}</span>
      <span class="name">{{ username }}</span>
      <ChevronDown :size="16" :stroke-width="2" class="chevron" />
    </button>

    <div v-if="open" class="menu" role="menu">
      <RouterLink
        :to="{ name: 'profile' }"
        role="menuitem"
        data-testid="user-menu-profile"
        @click="close"
      >
        <Settings :size="16" :stroke-width="2" />
        <span>{{ t('nav.profile') }}</span>
      </RouterLink>
      <button type="button" role="menuitem" class="danger" @click="logout">
        <LogOut :size="16" :stroke-width="2" />
        <span>{{ t('nav.logout') }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.user-menu {
  position: relative;
}

.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid rgb(226 232 240 / 0.9);
  background: rgb(255 255 255 / 0.8);
  color: #0f172a;
  border-radius: 999px;
  padding: 0.35rem 0.85rem 0.35rem 0.35rem;
  font: inherit;
  cursor: pointer;
}

.user-trigger:hover {
  background: #fff;
  border-color: #cbd5e1;
}

.avatar {
  width: 1.85rem;
  height: 1.85rem;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: #0e3b3a;
  color: #ecfdf8;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.name {
  font-size: 0.875rem;
  font-weight: 600;
  max-width: 9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chevron {
  color: #64748b;
}

.menu {
  position: absolute;
  top: calc(100% + 0.45rem);
  inset-inline-end: 0;
  min-width: 11.5rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 0.85rem;
  box-shadow: 0 12px 28px rgb(15 23 42 / 0.12);
  padding: 0.35rem;
  z-index: 30;
}

.menu a,
.menu button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  border: 0;
  background: transparent;
  color: #334155;
  font: inherit;
  font-size: 0.875rem;
  padding: 0.55rem 0.7rem;
  border-radius: 0.6rem;
  cursor: pointer;
  text-align: start;
  text-decoration: none;
}

.menu a:hover,
.menu button:hover {
  background: #f1f5f9;
  color: #0f172a;
  text-decoration: none;
}

.menu .danger {
  color: #e11d48;
}

.menu .danger:hover {
  background: #fff1f2;
  color: #be123c;
}

@media (max-width: 640px) {
  .name {
    display: none;
  }

  .user-trigger {
    padding-inline-end: 0.4rem;
  }
}
</style>
