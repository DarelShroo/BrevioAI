import { defineStore } from 'pinia';

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

export enum MenuBravioKeys {
  textToolBox = 'textToolBox',
  configuration = 'configuration',
}

export enum TextToolBoxKeys { 
  textToolBoxToSummary = 'text-tool-box-to-summary',
  textToolBoxToTranscription = 'text-tool-box-to-speech',
  textToolBoxToDocFile = 'text-tool-box-to-summary-doc-file',
}
 export enum ConfigurationKeys {
  configurationLanguage = 'configuration-language',
  configurationModel = 'configuration-gpt-model',
 }

 export const selectedKeysNames = {
  [TextToolBoxKeys.textToolBoxToSummary]: 'Audio Summary',
  [TextToolBoxKeys.textToolBoxToTranscription]: 'Audio Transcription',
  [TextToolBoxKeys.textToolBoxToDocFile]: 'To Doc File',
 } as Record<string, string>;