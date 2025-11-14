<template>
  <a-layout-header :style="{
    position: 'fixed',
    zIndex: 1,
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 16px',
    backgroundColor: '#1F1A1C',
  }">
    <div class="navbar-logo">
      <img src="/src/assets/images/brevio_logo.png" alt="logo" class="logo-image" @click="goHome()" />
    </div>

    <div class="logo-container">
      <span class="logo-text">Brevio</span>
    </div>

    <div class="menu-container" style="min-width: 230px;" v-if="!isMobile">
      <a-menu v-model:selectedKeys="selectedKeys" theme="dark" mode="horizontal" :style="{
        lineHeight: '64px',
        backgroundColor: '#1F1A1C',
        color: '#fff',
        flexGrow: 1,
        justifyContent: 'flex-end',
        display: 'flex',
      }" :reverseArrow="true">
        <template v-for="item in menuItems" :key="item.key">
          <template v-if="item.key !== 'logout'">
            <a-menu-item @click="() => handleClick(item)" :style="{
              backgroundColor: currentPath === item.path ? selectedColor : backgroundColor[item.key],
              color: '#fff',
              borderRadius: '0px'
            }">
              {{ item.label }}
            </a-menu-item>
          </template>
          <template v-else>
            <a-popconfirm title="¿Estás seguro de querer cerrar sesión?" ok-text="Yes" cancel-text="No"
              @confirm="logout()" @cancel="cancel()">
              <a-menu-item :style="{
                backgroundColor: currentPath === item.path ? selectedColor : backgroundColor[item.key],
                color: '#fff',
                borderRadius: '0px'
              }">
                {{ item.label }}
              </a-menu-item>
            </a-popconfirm>
          </template>
        </template>
      </a-menu>
    </div>
    <div class="hamburger-container" v-if="isMobile">
      <a-button @click="open = true" class="hamburger-button">
        ☰
      </a-button>
    </div>

    <a-drawer v-if="isMobile" v-model:open="open" placement="left" :closable="true" @close="open = false"
      :bodyStyle="{ backgroundColor: '#1F1A1C', color: '#fff' }">
      <a-menu v-model:selectedKeys="selectedKeys" theme="dark" mode="inline"
        :style="{ backgroundColor: '#25282F', color: '#fff' }">
        <div style="width: 100%;">
          <template v-for="item in menuItems" :key="item.key">
            <template v-if="item.key !== 'logout'">
            <a-menu-item @click="() => handleClick(item)" :style="{
              backgroundColor: currentPath === item.path ? selectedColor : primaryColor,
              color: '#fff',
              borderRadius: '0px',
            }">
              {{ item.label }}
            </a-menu-item>
          </template>
          <template v-else>
            <a-popconfirm title="¿Estás seguro de querer cerrar sesión?" ok-text="Yes" cancel-text="No"
              @confirm="logout()" @cancel="cancel()">
              <a-menu-item :style="{
                backgroundColor: currentPath === item.path ? selectedColor : primaryColor,
                color: '#fff',
                borderRadius: '0px',
              }">
                {{ item.label }}
              </a-menu-item>
            </a-popconfirm>
          </template>
          </template>
        </div>
      </a-menu>
    </a-drawer>
  </a-layout-header>
</template>

<script src="./NavBar.ts" lang="ts" />

<style src="./NavBar.css" scoped />
