<template>
  <a-space direction="vertical" style="width: 100%">
    <div>
      <a-input-search
        v-model:value="value"
        placeholder="Your url here"
        enter-button
        @search="onSearch"
      />
    </div>
  </a-space>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const value = ref('')
const onSearch = (value: string) => console.log(value)
</script>

<style scoped>
.padding {
  padding: 20px;
}

.ant-input-search-button{ 
  background-color: #242328!important;
  border-color: #242328 !important;
}
:where(.css-dev-only-do-not-override-1p3hq3p).ant-input-search .ant-input:hover, :where(.css-dev-only-do-not-override-1p3hq3p).ant-input-search .ant-input:focus{
    border-color: #70B3B2;
}

:where(.css-dev-only-do-not-override-1p3hq3p).ant-menu-dark:not(.ant-menu-horizontal) .ant-menu-submenu-title:active {
  background-color: #70B3B2;
}
</style>
