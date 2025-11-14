<template>
  <div class="login-container">
    <a-card class="login-card" bordered>
      <h2 class="login-title">Iniciar Sesión</h2>
      <a-form ref="formRef" :model="formState" :rules="rules" @finish="handleLogin">
        <a-form-item name="identity">
          <a-input v-model:value="formState.identity" placeholder="Usuario o Email" />
        </a-form-item>
        <a-form-item name="password">
          <a-input-password v-model:value="formState.password" placeholder="Contraseña" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" block class="login-button" :disabled="isDisabled"
            :loading="loading">
            Entrar
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script lang="ts" src="./LoginComponent.ts"></script>
<style scoped src="./LoginStyle.css" />
