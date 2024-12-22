<template>
  <div style="color: white; width: 100%;" v-if="menuBravioStore.getOpenKeys.includes('configuration')">
    <div id="language" class="language" v-if="menuBravioStore.selectedKeys.configuration === 'configuration-language'">
      <a-select
        v-model:value="selectedLanguage"
        show-search
        placeholder="Select a Language"
        style="width: 100%"
        :options="languageOptions"
        :filter-option="filterOption"
        @change="openNotificationWithIcon('language')"
      />
    </div>
    <div id="model" class="model" v-if="menuBravioStore.selectedKeys.configuration === 'configuration-gpt-model'">
      <a-select
        v-model:value="selectedModel"
        show-search
        placeholder="Select a Model"
        style="width: 100%"
        :options="modelOptions"
        :filter-option="filterOption"
        @change="openNotificationWithIcon('model')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { notification } from 'ant-design-vue'
import { useMenuBravioStore } from '@/stores/useMenuBravioStore'
import { useStoreDeviceType } from '@/stores/useStoreDeviceType' // Importar el store

const languageOptions = ref([
  { value: 'ES', label: 'ES' },
  { value: 'RU', label: 'RU' },
  { value: 'CU', label: 'CU' },
])

const modelOptions = ref([
  { value: 'gpt-4', label: 'gpt-4' },
  { value: 'gpt-o-4', label: 'gpt-0-4' },
  { value: 'gpt-3', label: 'gpt-3' },
])

const selectedModel = ref<string | undefined>(undefined)
const selectedLanguage = ref<string | undefined>(undefined)

const menuBravioStore = useMenuBravioStore()
const { isMobile } = useStoreDeviceType()

const openNotificationWithIcon = (select: 'language' | 'model') => {
  if (select === 'language') {
    notification['info']({
      message: 'Language',
      description:
        `You’ve selected "${selectedLanguage.value}". Now, let’s translate the text to this language!`,
      placement: placement.value
    });
  } else {
    notification['info']({
      message: 'GPT Model',
      description:
        `You have selected the ${selectedModel.value} GPT model. Now, let’s generate the text!`,
      placement: placement.value
    });
  }
}

const placement = computed(() => {
  return isMobile ? 'bottom' : 'topRight'
})

const filterOption = (input: string, option: any) => {
  return option.value.toLowerCase().indexOf(input.toLowerCase()) >= 0
}
</script>

<style scoped>
.model, .language {
  padding: 10px;
}


</style>
