<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { CreditCard, FilePlus, Library, LogIn, Menu, Settings, Sparkles, UserPlus } from '@lucide/vue'
import Drawer from 'primevue/drawer'
import AppLogo from '@/components/common/AppLogo.vue'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
import { useAuthStore } from '@/stores/auth.store'
import logoUrl from '@/assets/images/brevio_logo.png'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const drawerOpen = ref(false)

void auth.hydrate()

const isAuthed = computed(() => auth.isAuthenticated)
const active = computed(() => {
  const name = String(route.name || '')
  if (name === 'comparar' || name === 'comparar-slug') return 'comparar'
  if (name === 'plans') return 'plans'
  return name
})
const pageTitle = computed(() => {
  if (active.value === 'plans') return t('nav.plans')
  return t('demo.compareTitle')
})

/** Same order as AppSidebar: summary → store → plans → demo → profile (or auth links). */
const navItems = computed(() => {
  if (isAuthed.value) {
    return [
      { label: t('nav.summary'), icon: FilePlus, name: 'summary' as const },
      { label: t('nav.store'), icon: Library, name: 'store' as const },
      { label: t('nav.plans'), icon: CreditCard, name: 'plans' as const },
      { label: t('demo.badge'), icon: Sparkles, name: 'comparar' as const },
      { label: t('nav.profile'), icon: Settings, name: 'profile' as const },
    ]
  }
  return [
    { label: t('nav.plans'), icon: CreditCard, name: 'plans' as const },
    { label: t('demo.badge'), icon: Sparkles, name: 'comparar' as const },
    { label: t('auth.signIn'), icon: LogIn, name: 'login' as const },
    { label: t('auth.createAccount'), icon: UserPlus, name: 'register' as const },
  ]
})

async function logout() {
  drawerOpen.value = false
  await auth.logout()
  router.push({ name: 'login' })
}

function closeDrawer() {
  drawerOpen.value = false
}
</script>

<template>
  <div class="demo-shell">
    <aside class="desktop-nav" :aria-label="t('app.ariaPrimary')">
      <div class="sidebar">
        <div>
          <div class="brand">
            <AppLogo size="md" inverted />
          </div>
          <nav class="nav" :aria-label="t('nav.app')">
            <RouterLink
              v-for="item in navItems"
              :key="item.name"
              class="nav-item"
              :class="{ active: active === item.name }"
              :to="{ name: item.name }"
              :aria-current="active === item.name ? 'page' : undefined"
              :data-testid="`nav-${item.name}`"
            >
              <component :is="item.icon" :size="18" :stroke-width="2" aria-hidden="true" />
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>
        </div>
        <div class="footer">
          <LanguageSwitcher variant="ghost" class="sidebar-locale" />
          <button v-if="isAuthed" type="button" class="logout" @click="logout">
            {{ t('nav.logout') }}
          </button>
        </div>
      </div>
    </aside>

    <div class="main-column">
      <header class="topbar">
        <div class="topbar-left">
          <button
            type="button"
            class="icon-btn mobile-only"
            :aria-label="t('nav.open')"
            data-testid="demo-menu-toggle"
            @click="drawerOpen = true"
          >
            <Menu :size="20" :stroke-width="2" />
          </button>
          <div class="topbar-brand">
            <img
              :src="logoUrl"
              :alt="t('app.name')"
              class="topbar-logo"
              width="28"
              height="28"
            />
            <p class="topbar-title">{{ pageTitle }}</p>
          </div>
        </div>
      </header>

      <main class="content">
        <RouterView />
      </main>
    </div>

    <Drawer
      v-model:visible="drawerOpen"
      position="left"
      class="demo-mobile-drawer"
      :show-close-icon="false"
    >
      <div class="sidebar sidebar--drawer">
        <div>
          <div class="brand">
            <AppLogo size="md" inverted />
          </div>
          <nav class="nav" :aria-label="t('nav.app')">
            <RouterLink
              v-for="item in navItems"
              :key="`drawer-${item.name}`"
              class="nav-item"
              :class="{ active: active === item.name }"
              :to="{ name: item.name }"
              :aria-current="active === item.name ? 'page' : undefined"
              :data-testid="`nav-${item.name}-drawer`"
              @click="closeDrawer"
            >
              <component :is="item.icon" :size="18" :stroke-width="2" aria-hidden="true" />
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>
        </div>
        <div class="footer">
          <div class="locale-block">
            <p class="locale-label">{{ t('locale.label') }}</p>
            <LanguageSwitcher variant="ghost" class="sidebar-locale" />
          </div>
          <button v-if="isAuthed" type="button" class="logout" @click="logout">
            {{ t('nav.logout') }}
          </button>
        </div>
      </div>
    </Drawer>
  </div>
</template>

<style scoped>
.demo-shell {
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

.sidebar {
  box-sizing: border-box;
  width: 16rem;
  height: 100%;
  min-height: 100vh;
  flex-shrink: 0;
  background: #072d2d;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 1.5rem;
}

.sidebar--drawer {
  width: 100%;
  min-height: 100%;
  border: 0;
}

.brand {
  color: #fff;
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

.logout {
  color: #94a3b8;
}

.main-column {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  max-height: 100vh;
  overflow: auto;
}

.topbar {
  display: none;
  position: sticky;
  top: 0;
  z-index: 10;
  height: 4rem;
  min-height: 4rem;
  max-height: 4rem;
  padding: 0 1rem;
  align-items: center;
  border-bottom: 1px solid rgb(226 232 240 / 0.8);
  background: rgb(255 255 255 / 0.92);
  backdrop-filter: blur(8px);
  box-sizing: border-box;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}

.topbar-logo {
  width: 1.75rem;
  height: 1.75rem;
  flex-shrink: 0;
  object-fit: contain;
  border-radius: 0.4rem;
}

.topbar-title {
  margin: 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
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
  flex-shrink: 0;
}

.icon-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.content {
  flex: 1;
  min-width: 0;
  padding: 1.25rem;
  overflow: auto;
}

.mobile-only {
  display: none;
}

@media (max-width: 860px) {
  .desktop-nav {
    display: none;
  }

  .topbar {
    display: flex;
  }

  .mobile-only {
    display: inline-flex;
  }

  .content {
    padding: 1rem;
  }
}
</style>

<!-- Teleported Drawer leaves DemoLayout DOM; unscoped rules required for panel chrome. -->
<style>
.p-drawer.demo-mobile-drawer {
  width: min(16rem, 86vw) !important;
  max-width: min(16rem, 86vw) !important;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #072d2d;
  border: 0;
  box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.35);
}

.p-drawer.demo-mobile-drawer .p-drawer-header {
  display: none;
}

.p-drawer.demo-mobile-drawer .p-drawer-content {
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  padding: 0 !important;
  overflow: auto;
  background: #072d2d;
}

.p-drawer.demo-mobile-drawer .sidebar {
  width: 100%;
  min-height: 100%;
  border-inline-end: 0;
}
</style>
