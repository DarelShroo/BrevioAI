<template>
  <a-layout-content :style="{ marginTop: '64px' }">
    <div class="content-wrapper">
      <div class="container-bravio" :style="{ backgroundImage: `url(${backgroundImage})` }">
        <MenuBar />
        <div style="display: flex; flex-direction: column; width: 100%;" class="container-config">
          <div 
            :style="{ alignItems: 'center', marginTop: '20px' }"
            style="display: flex; justify-content: flex-end;" 
            class="container-config">
            <SearchBar />
          </div>
          <div 
            :style="{alignItems: 'center', justifyContent: 'center',padding: '0 5rem' }" 
            style="display: flex; justify-content: flex-end; height: initial !important;" 
            class="container-config">
            <ConfigBox />
          </div>
        </div>
      </div>
    </div>
  </a-layout-content>
</template>

<script setup lang="ts">
import backgroundImage from '@/assets/images/ia-transformed.jpeg';
</script>

<style scoped>
.content-wrapper {
  min-height: calc(100vh - 128px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5px;
  background: linear-gradient(135deg, 
    #252429, 
    #8CF0F5, 
    #1F1A1C, 
    #C1FBF8);
  background-size: 400% 100%;
  animation: gradientAnimation 50s ease infinite;
  margin: 0;
}

.container-bravio {
  display: flex;
  min-height: 20rem;
  padding: 5px;
  width: 50rem;
  height: 100%;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  background-size: cover;
  background-repeat: no-repeat;
  position: relative;
}

.container-config {
  padding: 5px;
  width: 100%;
  align-items: center !important;
  justify-content: center !important;
}

@keyframes gradientAnimation {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

@media (max-width: 768px) {
  .container-bravio {
    width: 100%;
  }

  .container-config {
    padding: 0;
  }
}
</style>
