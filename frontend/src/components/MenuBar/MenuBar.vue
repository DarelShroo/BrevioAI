<template>
  <a-menu
    mi-a-menu="amigue"
    :openKeys="menuBravioStore.openKeys"
    :selectedKeys="selectedKeysArray"
    @update:openKeys="menuBravioStore.openKeys = $event"
    @update:selectedKeys="handleSelectedKeys"
    style="width: 256px; border-radius: 10px"
    mode="inline"
    :theme="theme"
    :items="items"
  />
</template>

<style src="./MenuBar.css" scoped />

<script src="./MenuBar.ts" lang="ts" />

