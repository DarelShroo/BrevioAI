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

<script src="./NavBar.ts" lang="ts" />

<style src="./NavBar.css" scoped />
