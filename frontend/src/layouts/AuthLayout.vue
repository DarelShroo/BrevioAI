<script setup lang="ts">
import AuthHeroPanel from '@/components/auth/AuthHeroPanel.vue'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
import logoBgUrl from '@/assets/images/logo-bg.png'
</script>

<template>
  <div class="auth-shell">
    <AuthHeroPanel />
    <div class="auth-panel card-surface">
      <div class="locale-row">
        <img :src="logoBgUrl" alt="Brevio Logo" class="mobile-logo" />
        <LanguageSwitcher />
      </div>
      <RouterView />
    </div>
  </div>
</template>

<style scoped>
.auth-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: var(--bv-space-6);
  padding: 0;
  align-items: stretch;
}

.auth-panel {
  width: min(100%, 440px);
  justify-self: center;
  align-self: center;
  padding: var(--bv-space-6);
}

.locale-row {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: var(--bv-space-4);
}

.mobile-logo {
  display: none;
}

@media (max-width: 1023px) {
  .auth-shell {
    grid-template-columns: 1fr;
    padding: var(--bv-space-4);
  }

  .locale-row {
    justify-content: space-between;
  }

  .mobile-logo {
    display: block;
    height: 2.5rem;
    width: auto;
    object-fit: contain;
  }
}
</style>
