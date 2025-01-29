<template>
  <a-space direction="vertical" style="width: 100%">
    <div>
      <a-input-search
        placeholder="Your url here"
        enter-button
        @search="onSearch"
        v-model:value="searchValue"
      />
    </div>
  </a-space>
</template>

<script src="./SearchBar.ts" lang="ts" />

<style src="./SearchBar.css" scoped />