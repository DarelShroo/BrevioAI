<template>
  <div class="a-layout-content">
  <a-layout-content class="">
    <div class="content-wrapper">
      <div class="container-bravio " :style="{ backgroundImage: `url(${backgroundImage})` }">
        <MenuBar />
        <div class="container-config">
          <div class="config-element-selected">
            <div v-text="selectedKeysNames[useMenuBravio.combinedSelectedKeys[0]]"></div>
          </div>
          <div 
            class="container-config mt-20px search-bar">
            <SearchBar />
          </div>
          <div 
            style="" 
            class="container-config config-box">
            <ConfigBox />
          </div>
        </div>
      </div>
    </div>
  </a-layout-content>
</div>
</template>

<script lang="ts" src="./ContentHome.ts" />

<style src="./ContentHome.css" scoped />
