<template>
  <a-menu
    :openKeys="menuBravioStore.openKeys"
    :selectedKeys="selectedKeysArray"
    @update:openKeys="menuBravioStore.openKeys = $event"
    @update:selectedKeys="handleSelectedKeys"
    style="width: 256px; border-radius: 10px"
    mode="inline"
    :theme="theme"
    :items="items"
  />
</template>

<style lang="css">
.container-bravio {
  border-radius: 10px;
}

.container-bravio ul {
  background-color: #272429 !important;
  font-size: 1.15rem;
}

.container-bravio ul ul li {
  background-color: #1f1a1c !important;
}

.ant-menu {
  margin-right: 10px;
}

@media screen and (max-width: 500px) {
  .container-bravio {
    flex-direction: column !important;
    width: 100% !important;
  }
  .ant-menu {
    margin-bottom: 10px;
    margin-right: 0px;
    width: 100% !important;
  }
}
</style>

<script lang="ts" setup>
import { ref, computed, h} from 'vue';
import { AppstoreOutlined, SettingOutlined } from '@ant-design/icons-vue';
import { useMenuBravioStore } from '@/stores/useMenuBravioStore';
import OpenAiIcon from '@/assets/images/openai-icon.svg';
import LanguageIcon from '@/assets/images/language-icon2.svg';

const theme = ref('dark');
const menuBravioStore = useMenuBravioStore();

const selectedKeysArray = computed(() => [
  menuBravioStore.selectedKeys.textToolBox,
  menuBravioStore.selectedKeys.configuration,
].filter(Boolean));


function handleSelectedKeys(keys: string[]) {
  keys.forEach(key => {
    if (key.startsWith('text-tool-box')) {
      menuBravioStore.selectedKeys.textToolBox = key;
    } else if (key.startsWith('configuration')) {
      menuBravioStore.selectedKeys.configuration = key;
    }
  });
}

const items = ref([
  {
    key: 'text-tool-box',
    icon: () => h(AppstoreOutlined),
    label: 'Text Tool Box',
    children: [
      {
        key: 'text-tool-box-to-summary',
        label: 'Audio Summary',
        onClick: () => menuBravioStore.toggleSelectKey('text-tool-box-to-summary', 'textToolBox'),
      },
      {
        key: 'text-tool-box-to-speech',
        label: 'Audio Transcription',
        onClick: () => menuBravioStore.toggleSelectKey('text-tool-box-to-speech', 'textToolBox'),
      },
      {
        key: 'text-tool-box-to-summary-doc-file',
        label: 'To Doc File',
        onClick: () =>
          menuBravioStore.toggleSelectKey('text-tool-box-to-summary-doc-file', 'textToolBox'),
      },
    ],
  },
  {
    key: 'configuration',
    icon: () => h(SettingOutlined),
    label: 'Configuration',
    children: [
      {
        key: 'configuration-language',
        icon: () =>
          h('img', {
            src: LanguageIcon,
            alt: 'Language',
            style: { width: '24px', height: '24px' },
          }),
        label: 'Language',
        onClick: () => menuBravioStore.toggleSelectKey('configuration-language', 'configuration'),
      },
      {
        key: 'configuration-gpt-model',
        icon: () =>
          h('img', {
            src: OpenAiIcon,
            alt: 'GPT Model',
            style: { width: '24px', height: '24px' },
          }),
        label: 'GPT Model',
        onClick: () => menuBravioStore.toggleSelectKey('configuration-gpt-model', 'configuration'),
      },
    ],
  },
]);
</script>
