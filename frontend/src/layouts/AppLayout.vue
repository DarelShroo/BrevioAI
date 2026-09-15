<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { Menu } from '@lucide/vue'
import Drawer from 'primevue/drawer'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
import UserMenu from '@/components/layout/UserMenu.vue'
import { useAuthStore } from '@/stores/auth.store'
import { useRealtimeNotifications } from '@/composables/useRealtimeNotifications'
import constellationUrl from '@/assets/images/auth-constellation.svg?url'
import documentsUrl from '@/assets/images/auth-documents.svg?url'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const drawerOpen = ref(false)
useRealtimeNotifications()

const title = computed(() => {
  if (route.name === 'summary') return t('pages.createSummary')
  if (route.name === 'store') return t('pages.store')
  if (route.name === 'profile') return t('pages.profile')
  return t('pages.brevio')
})

const isWide = computed(() => route.name === 'store')

async function logout() {
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="app-shell">
    <aside class="desktop-nav" :aria-label="t('app.ariaPrimary')">
      <AppSidebar @logout="logout" />
    </aside>

    <div class="app-main">
      <img :src="constellationUrl" alt="" class="mesh" aria-hidden="true" />
      <img :src="documentsUrl" alt="" class="docs" aria-hidden="true" />

      <header class="topbar">
        <div class="topbar-left">
          <button
            type="button"
            class="icon-btn mobile-only"
            :aria-label="t('nav.open')"
            @click="drawerOpen = true"
          >
            <Menu :size="20" :stroke-width="2" />
          </button>
          <div>
            <p class="brand-mobile mobile-only">{{ t('app.name') }}</p>
            <p class="topbar-title">{{ title }}</p>
          </div>
        </div>
        <div class="topbar-right">
          <LanguageSwitcher variant="ghost" />
          <UserMenu @logout="logout" />
        </div>
      </header>

      <main class="content" :class="{ page: !isWide }">
        <RouterView />
      </main>
    </div>

    <Drawer v-model:visible="drawerOpen" position="left" class="mobile-drawer">
      <AppSidebar @logout="logout" @navigate="drawerOpen = false" />
    </Drawer>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: #f8fafc;
}

.desktop-nav {
  position: sticky;
  top: 0;
  height: 100vh;
  flex-shrink: 0;
  z-index: 20;
}

.app-main {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;
  max-height: 100vh;
}

.mesh,
.docs {
  position: absolute;
  pointer-events: none;
  z-index: 0;
}

.mesh {
  right: 0;
  bottom: 0;
  width: min(72%, 920px);
  height: 70%;
  object-fit: cover;
  object-position: bottom right;
  opacity: 0.7;
}

.docs {
  top: 4.5rem;
  right: 1.5rem;
  width: 220px;
  opacity: 0.55;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  min-height: 4.25rem;
  padding: 0.85rem 1.75rem 0.85rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid rgb(226 232 240 / 0.8);
  background: rgb(255 255 255 / 0.6);
  backdrop-filter: blur(8px);
}

.topbar-left,
.topbar-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.topbar-right {
  gap: 0.9rem;
  padding: 0.15rem 0.15rem 0.15rem 0.5rem;
}

.topbar-title {
  margin: 0;
  font-family: var(--bv-font-sans);
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.brand-mobile {
  margin: 0;
  color: #0f766e;
  font-family: var(--bv-font-serif);
  font-optical-sizing: auto;
  font-weight: 700;
  font-size: 0.75rem;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border: 0;
  border-radius: 0.65rem;
  background: transparent;
  color: #334155;
  cursor: pointer;
}

.icon-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.content {
  position: relative;
  z-index: 1;
  padding: 1.5rem 2rem 2rem;
}

.mobile-only {
  display: none;
}

:deep(.mobile-drawer.p-drawer) {
  background: #072d2d;
  width: min(16rem, 86vw);
}

:deep(.mobile-drawer .p-drawer-header) {
  display: none;
}

:deep(.mobile-drawer .p-drawer-content) {
  padding: 0;
  background: #072d2d;
}

@media (max-width: 900px) {
  .desktop-nav {
    display: none;
  }

  .mobile-only {
    display: inline-flex;
  }

  .topbar {
    padding: 0.75rem 1rem;
  }

  .content {
    padding: 1.15rem 1rem 1.5rem;
  }

  .docs {
    display: none;
  }
}
</style>
