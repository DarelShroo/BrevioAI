<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SyncCompareDemo from '@/components/demo/SyncCompareDemo.vue'
import { useAuthStore } from '@/stores/auth.store'

const route = useRoute()
const auth = useAuthStore()

const slug = computed(() => {
  const raw = route.params.slug
  return typeof raw === 'string' && raw.trim() ? raw.trim() : undefined
})

const preferCategory = computed(() =>
  typeof route.query.category === 'string' ? route.query.category : null,
)
const preferStyle = computed(() =>
  typeof route.query.style === 'string' ? route.query.style : null,
)
const preferModel = computed(() =>
  typeof route.query.model === 'string' ? route.query.model : null,
)

const showRegisterCta = computed(() => !auth.isAuthenticated)
</script>

<template>
  <div class="compare-page page" data-testid="compare-view">
    <SyncCompareDemo
      :slug="slug"
      :prefer-category="preferCategory"
      :prefer-style="preferStyle"
      :prefer-model="preferModel"
      :show-register-cta="showRegisterCta"
    />
  </div>
</template>

<style scoped>
.compare-page {
  width: min(100%, 1280px);
  margin: 0 auto;
  padding-bottom: 1.5rem;
}
</style>
