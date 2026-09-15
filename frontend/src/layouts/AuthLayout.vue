<script setup lang="ts">
import AuthHeroPanel from '@/components/auth/AuthHeroPanel.vue'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
</script>

<template>
  <div class="auth-shell">
    <AuthHeroPanel />
    <div class="auth-panel card-surface">
      <div class="locale-row">
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
  margin-bottom: var(--bv-space-4);
}

@media (max-width: 1023px) {
  .auth-shell {
    grid-template-columns: 1fr;
    padding: var(--bv-space-4);
  }
}
</style>
