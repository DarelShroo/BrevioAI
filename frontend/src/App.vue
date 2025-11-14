<script setup lang="ts">
import HomeView from '@/modules/content/components/Home/HomeView.vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from './stores/useAuthStore';

const authStore = useAuthStore();
const router = useRouter();

if (!authStore.userLoggedIn) {
  router.push("/auth/login");
}
</script>

<template id="app">
  <HomeView></HomeView>
</template>

<style lang="css">
.ant-input-search-button {
  background-color: #242328 !important;
  border-color: #242328 !important;
}

:where(.css-dev-only-do-not-override-1p3hq3p).ant-input-search .ant-input:hover,
:where(.css-dev-only-do-not-override-1p3hq3p).ant-input-search .ant-input:focus {
  border-color: #70b3b2;
}

:where(.css-dev-only-do-not-override-1p3hq3p).ant-menu-dark:not(.ant-menu-horizontal) .ant-menu-submenu-title:active {
  background-color: #70b3b2;
}

:where(.css-dev-only-do-not-override-1p3hq3p).ant-select:not(.ant-select-disabled):not(.ant-select-customize-input):not(.ant-pagination-size-changer):hover .ant-select-selector {
  border-color: #70b3b2 !important;
}

:where(.css-dev-only-do-not-override-1p3hq3p).ant-input {
  border-top-left-radius: initial !important;
}

.container-bravio ul {
  background-color: #272429 !important;
  font-size: 1.15rem;
  min-width: 270px;
}

.container-bravio ul ul li {
  background-color: #1f1a1c !important;
}

.ant-menu {
  margin-right: 10px;
}

@media screen and (max-width: 500px) {
  .container-bravio {
    flex-direction: column !important;
    width: 100% !important;
  }

  .ant-menu {
    margin-bottom: 10px;
    margin-right: 0px;
    width: 100% !important;
  }
}
</style>
