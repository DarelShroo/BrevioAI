import { reactive, ref, computed, onMounted } from 'vue';

export const useStoreDeviceType = () => {
  const isMobile = ref(false);

  const globalWindow = reactive({
    innerWidth: window.innerWidth
  });

  const checkIsMobile = () => {
    isMobile.value = globalWindow.innerWidth <= 480;
  };

  onMounted(() => {
    checkIsMobile();
  });

  window.addEventListener('resize', () => {
    globalWindow.innerWidth = window.innerWidth;
    checkIsMobile();
  });

  return {
    isMobile,
    placement: computed(() => isMobile.value ? 'bottom' : 'topRight')
  };
};
