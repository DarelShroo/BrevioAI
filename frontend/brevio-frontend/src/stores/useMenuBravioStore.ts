import { defineStore } from 'pinia';

export const useMenuBravioStore = defineStore('menuBravio', {
  state: () => ({
    openKeys: ['text-tool-box'] as string[],
    selectedKeys: {
      textToolBox: 'text-tool-box-to-summary',
      configuration: 'configuration-language', 
    },
  }), 
  actions: {
    toggleOpenKey(key: string) {
      if (this.openKeys.includes(key)) {
        this.openKeys = this.openKeys.filter(item => item !== key);
      } else {
        this.openKeys.push(key);
      }
    },
    toggleSelectKey(key: string, category: 'textToolBox' | 'configuration') {
      this.selectedKeys[category] = key;
    },
  },
  getters: {
    combinedSelectedKeys: (state) => [
      state.selectedKeys.textToolBox,
      state.selectedKeys.configuration,
    ],
    getOpenKeys: (state) => state.openKeys,
  },
});
