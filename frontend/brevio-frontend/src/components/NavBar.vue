<template>
  <a-layout-header :style="{ position: 'fixed', zIndex: 1, width: '100%' }">
    <div class="logo" />

    <a-menu
      v-if="!isMobile"
      v-model:selectedKeys="selectedKeys"
      theme="dark"
      mode="horizontal"
      :style="{ lineHeight: '64px', backgroundColor: '#1F1A1C', color: '#fff', justifyContent: 'flex-end' }"
            :reverseArrow="true"
    >
      <template v-for="item in menuItems" :key="item.key">
        <a-menu-item
          @click="changeColor(item.key)"
          :style="{
            backgroundColor: currentPath === item.path ? selectedColor : backgroundColor[item.key],
            color: '#fff',
          }"
        >
          {{ item.label }}
        </a-menu-item>
      </template>
    </a-menu>

    <a-drawer
      v-if="isMobile"
      v-model:open="open"
      placement="left"
      :closable="true"
      @close="open = false"
      :bodyStyle="{ backgroundColor: '#1F1A1C', color: '#fff' }"
    >
      <a-menu
        v-model:selectedKeys="selectedKeys"
        theme="dark"
        mode="inline"
        :style="{ backgroundColor: '#25282F', color: '#fff' }"
      >
        <template v-for="item in menuItems" :key="item.key">
          <a-menu-item
            @click="changeColor(item.key)"
            :style="{
              backgroundColor: currentPath === item.path ? selectedColor : primaryColor,
              color: '#fff',
            }"
          >
            {{ item.label }}
          </a-menu-item>
        </template>
      </a-menu>
    </a-drawer>

    <a-button
      v-if="isMobile"
      @click="open = true"
      class="hamburger-button"
    >
      ☰
    </a-button>
  </a-layout-header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useStoreDeviceType } from '@/stores/useStoreDeviceType'

const open = ref<boolean>(false)
const selectedKeys = ref(['1'])
const route = useRoute()
const currentPath = ref<string>(route.path)
const primaryColor = ref<string>('#1F1A1C')
const selectedColor = ref<string>('#25282F')
const { isMobile } = useStoreDeviceType()

const backgroundColor = ref<{ [key: string]: string }>({
  login: primaryColor.value,
  register: primaryColor.value,
  bravio: primaryColor.value,
})

const menuItems = ref([
  { key: 'login', path: '/login', label: 'Login' },
  { key: 'register', path: '/register', label: 'Register' },
  { key: 'bravio', path: '/bravio', label: 'Bravio' },
])

const changeColor = (key: string) => {
  Object.keys(backgroundColor.value).forEach((k) => (backgroundColor.value[k] = primaryColor.value))

  backgroundColor.value[key] = selectedColor.value
}
</script>

<style scoped>
header {
  background-color: #1f1a1c !important;
  color: #fff;
}

.hamburger-button {
  position: absolute;
  top: 10px;
  right: 10px;
}

.ant-menu-item:hover {
  background-color: #25282F !important; 
  color: #fff !important;
}

:deep(.ant-menu-item:hover) {
  background-color: #25282F !important;
  color: #fff !important;
}

:deep(.ant-drawer-header) {
  background-color: #1f1a1c !important;
  color: #fff !important;
}

:deep(.ant-drawer-body) {
  background-color: #1f1a1c !important;
  color: #fff !important;
}

.ant-menu {
  background-color: #1f1a1c !important;
  color: #fff !important;
}

.ant-menu-item {
  color: #fff !important;
}

.ant-menu-item-selected {
  background-color: #25282F !important;
  color: #fff !important;
}
</style>
