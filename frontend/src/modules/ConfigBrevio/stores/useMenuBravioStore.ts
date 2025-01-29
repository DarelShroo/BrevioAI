import { defineStore } from 'pinia';
import { ConfigurationKeys } from '../enums/configuration-keys.enum';
import { TextToolBoxKeys } from '../enums/text-tool-box-keys.enum';
import { MenuBravioKeys } from '../enums/menu-bravio-keys';

export const useMenuBravioStore = defineStore('menuBravio', {
  state: () => ({
    openKeys: ['text-tool-box'] as string[],
    selectedKeys: {
      textToolBox: TextToolBoxKeys.textToolBoxToSummary,
      configuration: ConfigurationKeys.configurationLanguage,
    } as Record<MenuBravioKeys, string>,
  }),
  actions: {
    toggleOpenKey(key: string) {
      if (this.openKeys.includes(key)) {
        this.openKeys = this.openKeys.filter(item => item !== key);
      } else {
        this.openKeys.push(key);
      }
    },
    toggleSelectKey(key: string, category: MenuBravioKeys.textToolBox| MenuBravioKeys.configuration) {
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

