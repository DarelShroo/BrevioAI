<script setup lang="ts">
import AppLogo from '@/components/common/AppLogo.vue'
import constellationUrl from '@/assets/images/auth-constellation.svg?url'
import documentsUrl from '@/assets/images/auth-documents.svg?url'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <aside class="auth-hero" :aria-label="t('app.name')">
    <div class="hero-glow" aria-hidden="true" />
    <img :src="constellationUrl" alt="" class="hero-mesh" aria-hidden="true" />
    <img :src="documentsUrl" alt="" class="hero-docs" aria-hidden="true" />
    <div class="hero-content">
      <AppLogo size="md" inverted />
      <div class="hero-copy">
        <h1 class="font-serif">{{ t('auth.headline') }}</h1>
        <p>{{ t('auth.subtitle') }}</p>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.auth-hero {
  display: none;
  position: relative;
  isolation: isolate;
  overflow: hidden;
  min-height: 100vh;
  color: #fff;
  background:
    radial-gradient(ellipse 90% 60% at 12% 88%, rgba(92, 186, 176, 0.22), transparent 58%),
    radial-gradient(circle at 86% 12%, rgba(255, 255, 255, 0.07), transparent 36%),
    linear-gradient(165deg, #166963 0%, #0f5853 46%, #0c4642 100%);
}

.hero-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse 70% 50% at 30% 55%, rgba(20, 80, 76, 0.18), transparent 70%);
  pointer-events: none;
}

.hero-mesh {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 58%;
  object-fit: cover;
  object-position: bottom;
  pointer-events: none;
  opacity: 0.78;
}

.hero-docs {
  position: absolute;
  top: 32%;
  right: -0.35rem;
  width: min(40%, 230px);
  pointer-events: none;
  z-index: 2;
  filter: drop-shadow(0 12px 18px rgba(11, 61, 57, 0.18));
}

.hero-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2.75rem;
  height: 100%;
  max-width: 34rem;
  padding: 4rem 4.5rem 5.5rem;
}

.hero-copy h1 {
  margin: 0 0 1.15rem;
  color: #fff;
  font-family: var(--bv-font-serif);
  font-optical-sizing: auto;
  font-size: clamp(2.15rem, 3.6vw, 3.15rem);
  font-weight: 600;
  line-height: 1.12;
  letter-spacing: -0.03em;
  max-width: 16.5ch;
}

.hero-copy p {
  margin: 0;
  max-width: 38ch;
  color: rgba(220, 242, 237, 0.82);
  font-size: 0.95rem;
  line-height: 1.55;
}

.hero-content :deep(.mark) {
  width: 3.15rem;
  height: 3.15rem;
  border-radius: 0.9rem;
}

.hero-content :deep(.wordmark strong) {
  font-size: 1.28rem;
}

@media (min-width: 1024px) {
  .auth-hero {
    display: flex;
  }
}
</style>
