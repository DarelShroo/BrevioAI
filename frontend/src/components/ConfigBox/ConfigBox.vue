<template>
  <div class="container-configbox" v-if="menuBravioStore.getOpenKeys.includes('configuration')">
    <Transition name="slide-fade">
    <div id="language" class="language" v-if="menuBravioStore.selectedKeys.configuration === 'configuration-language'">
      <a-select
        v-model:value="selectedLanguage"
        show-search
        :placeholder="placeHolderSelectedLanguage"
        class="a-select"
        :options="languageOptions"
        :filter-option="filterOption"
        @change="openNotificationWithIcon('language')"
      />
    </div>
  </Transition>
  <Transition name="slide-fade">
  <div id="model" class="model" v-if="menuBravioStore.selectedKeys.configuration === 'configuration-gpt-model'">
    <a-select
      v-model:value="selectedModel"
      show-search
      :placeholder="placeHolderSelectedModel"
      class="a-select"
      :options="modelOptions"
      :filter-option="filterOption"
      @change="openNotificationWithIcon('model')"
    />
  </div>
</Transition>

  </div>
</template>

<script lang="ts" src="./ConfigBox.ts" />


<style  src="./ConfigBox.css" scoped />
