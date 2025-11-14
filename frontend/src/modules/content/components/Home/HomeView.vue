<script setup lang="ts">
import ContentHome from '@/modules/content/components/ContentHome/ContentHome.vue';
import FooterBar from '@/modules/content/components/FooterBar/FooterBar.vue';
import NavBar from '@/modules/content/components/NavBar/NavBar.vue';
</script>


<template>
  <a-layout>
    <nav-bar></nav-bar>
    <content-home></content-home>
    <footer-bar></footer-bar>
  </a-layout>
</template>


<style scoped></style>
