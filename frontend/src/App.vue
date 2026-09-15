<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import { useCatalogStore } from '@/stores/catalog.store'
import { jobIdFromToastClass } from '@/utils/events'

const catalog = useCatalogStore()
const router = useRouter()

onMounted(() => {
  void catalog.loadAll().catch(() => undefined)
})

function onJobToastClick(event: { message?: { styleClass?: unknown } }) {
  const jobId = jobIdFromToastClass(event.message?.styleClass)
  if (jobId) {
    void router.push({ name: 'store', query: { entry: jobId } })
  }
}
</script>

<template>
  <Toast position="top-right" :onClick="onJobToastClick" />
  <RouterView />
</template>
