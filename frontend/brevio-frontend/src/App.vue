<script setup lang="ts">
import  HomeView  from './views/HomeView.vue';
</script>

<template id="app">
    <HomeView></HomeView>
</template>

<style lang="css">
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

:where(.css-dev-only-do-not-override-1p3hq3p).ant-select:not(.ant-select-disabled):not(.ant-select-customize-input):not(.ant-pagination-size-changer):hover .ant-select-selector{
  border-color: #70B3B2 !important;
}

</style>