<template>
  <div class="register-container">
    <a-card class="register-card" bordered>
      <h2 class="register-title">Registro</h2>
      <a-form ref="formRef" :model="formState" :rules="rules" @finish="handleRegister">
        <a-form-item name="username">
          <a-input v-model:value="formState.username" placeholder="Username" />
        </a-form-item>
        <a-form-item name="email">
          <a-input v-model:value="formState.email" placeholder="Email" />
        </a-form-item>
        <a-form-item name="password">
          <a-input-password v-model:value="formState.password" placeholder="Contraseña" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" block class="register-button" :disabled="isDisabled"
            :loading="loading">
            Registrar
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script lang="ts" src="./RegisterComponent.ts"></script>
<style scoped src="./RegisterStyle.css" />
