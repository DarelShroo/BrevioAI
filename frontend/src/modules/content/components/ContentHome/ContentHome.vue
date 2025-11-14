<template>
  <div class="a-layout-content" style="height: 100%">
    <a-layout-content class="" style="height: 100%">
      <div class="content-wrapper" style="height: 100%">
        <login-view v-if="route.path === '/auth/login'"></login-view>
        <register-view v-if="route.path === '/auth/register'"></register-view>
        <content-brevio v-if="route.path === '/brevio'"></content-brevio>
      </div>
    </a-layout-content>
  </div>
</template>

<script lang="ts" src="./ContentHome.ts" />

<style src="./ContentHome.css" scoped />
