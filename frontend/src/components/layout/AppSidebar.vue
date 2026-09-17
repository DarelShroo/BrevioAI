<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { CreditCard, FilePlus, Library, LogOut, Settings, Sparkles } from '@lucide/vue'
import AppLogo from '@/components/common/AppLogo.vue'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'

withDefaults(
  defineProps<{
    showLocale?: boolean
  }>(),
  { showLocale: false },
)

const emit = defineEmits<{
  logout: []
  navigate: []
}>()

const { t } = useI18n()
const route = useRoute()

const items = computed(() => [
  { label: t('nav.summary'), icon: FilePlus, name: 'summary' },
  { label: t('nav.store'), icon: Library, name: 'store' },
  { label: t('nav.plans'), icon: CreditCard, name: 'plans' },
  { label: t('demo.badge'), icon: Sparkles, name: 'comparar' },
  { label: t('nav.profile'), icon: Settings, name: 'profile' },
])

const active = computed(() => {
  const name = String(route.name || '')
  if (name === 'comparar' || name === 'comparar-slug') return 'comparar'
  return name
})
</script>

<template>
  <div class="sidebar">
    <div>
      <div class="brand">
        <AppLogo size="md" inverted />
      </div>

      <nav class="nav" :aria-label="t('nav.app')">
        <RouterLink
          v-for="item in items"
          :key="item.name"
          :to="{ name: item.name }"
          class="nav-item"
          :class="{ active: active === item.name }"
          :aria-current="active === item.name ? 'page' : undefined"
          :data-testid="`nav-${item.name}`"
          @click="emit('navigate')"
        >
          <component :is="item.icon" :size="18" :stroke-width="2" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </div>

    <div class="footer">
      <div v-if="showLocale" class="locale-block">
        <p class="locale-label">{{ t('locale.label') }}</p>
        <LanguageSwitcher variant="ghost" class="sidebar-locale" />
      </div>
      <button type="button" class="logout" data-testid="nav-logout" @click="emit('logout')">
        <LogOut :size="18" :stroke-width="2" aria-hidden="true" />
        <span>{{ t('nav.logout') }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.sidebar {
  box-sizing: border-box;
  height: 100%;
  min-height: 100vh;
  width: 16rem;
  max-width: 100%;
  background: #072d2d;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 1.5rem;
  border-inline-end: 1px solid rgb(4 47 46 / 0.4);
}

.brand {
  color: #fff;
}

.brand :deep(.tagline) {
  color: #cbd5e1;
  opacity: 0.86;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-top: 2rem;
}

.nav-item,
.logout {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  border: 0;
  background: transparent;
  color: #94a3b8;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  cursor: pointer;
  text-align: start;
  text-decoration: none;
  font-family: var(--bv-font-sans);
  font-size: 0.925rem;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.nav-item:hover,
.logout:hover {
  color: #fff;
  background: rgb(19 78 74 / 0.3);
  text-decoration: none;
}

.nav-item.active {
  background: #0e3b3a;
  color: #fff;
  font-weight: 500;
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.08);
  border-inline-start: 4px solid #2dd4bf;
  padding-inline-start: calc(0.75rem - 4px);
}

.footer {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.locale-block {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.25rem 0.15rem 0.5rem;
  border-bottom: 1px solid rgb(148 163 184 / 0.18);
}

.locale-label {
  margin: 0;
  padding-inline: 0.75rem;
  color: #94a3b8;
  font-family: var(--bv-font-sans);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.sidebar-locale {
  width: 100%;
}

.sidebar-locale :deep(.locale-select),
.sidebar-locale :deep(.p-select) {
  width: 100%;
  min-width: 0;
  color: #e2e8f0;
}

.sidebar-locale :deep(.p-select) {
  background: rgb(19 78 74 / 0.35);
  border: 1px solid rgb(148 163 184 / 0.2);
  border-radius: 0.5rem;
}

.sidebar-locale :deep(.p-select:not(.p-disabled).p-focus) {
  background: rgb(19 78 74 / 0.5);
  box-shadow: none;
}

.sidebar-locale :deep(.p-select-label),
.sidebar-locale :deep(.p-select-dropdown) {
  color: #e2e8f0;
}

.logout {
  color: #94a3b8;
}
</style>
