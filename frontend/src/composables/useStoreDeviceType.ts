import { reactive, ref, watch, computed } from 'vue';

export const useStoreDeviceType = () => {
  const isMobile = ref(false);
  const placement = computed(() => {
    return isMobile.value ? 'bottom' : 'topRight'
  })
  const globalWindow = reactive({
    innerWidth: window.innerWidth
  });  

  watch(() => globalWindow.innerWidth, (newInnerWidth) => {
    isMobile.value = newInnerWidth <= 480;
  });

  window.addEventListener('resize', () => {
    globalWindow.innerWidth = window.innerWidth;
  });

  return { isMobile, placement };
};
