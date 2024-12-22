// src/stores/useStoreDeviceType.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useStoreDeviceType = defineStore('deviceType', () => {
  const isMobile = ref(false);

  const updateDeviceType = () => {
    const width = window.innerWidth;
    isMobile.value = width <= 480;
  };

  window.addEventListener('resize', updateDeviceType);

  updateDeviceType();

  return { isMobile, updateDeviceType };
});
