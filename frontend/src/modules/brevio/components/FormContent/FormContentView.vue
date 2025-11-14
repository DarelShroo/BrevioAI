<template>
  <a-form :label-col="labelCol" :wrapper-col="wrapperCol" @submit.prevent="onSubmit"
    style="display:flex; flex-direction:column; align-items:center; justify-content:center">
    <div class="form-content" >
      <a-form-item labelAlign="left" labelWrap :label-col="{ span: 10 }" :wrapper-col="{ span: 14 }" label="Language"
        v-bind="validateInfos.language">
        <a-select v-model:value="modelRef.language" showSearch :filterOption="true" :options="languageOptions"
          placeholder="please select output language" />
      </a-form-item>
      <a-form-item labelAlign="left" labelWrap :label-col="{ span: 10 }" :wrapper-col="{ span: 14 }" label="Model"
        v-bind="validateInfos.model">
        <a-select v-model:value="modelRef.model" :options="modelOptions" placeholder="please select llm model" />
      </a-form-item>
      <a-form-item labelAlign="left" labelWrap :label-col="{ span: 10 }" :wrapper-col="{ span: 14 }" label="Category"
        v-bind="validateInfos.category">
        <a-select v-model:value="modelRef.category" :options="categoryOptions" @change="onCategoryChange()"
          placeholder="please select summary category type" />
      </a-form-item>
      <a-form-item labelAlign="left" labelWrap :label-col="{ span: 10 }" :wrapper-col="{ span: 14 }" label="Style"
        v-bind="validateInfos.style">
        <a-select v-model:value="modelRef.style" :options="getStyleOptions(modelRef.category || '')"
          placeholder="please select category style">
        </a-select>
      </a-form-item>
      <a-form-item labelAlign="left" labelWrap :label-col="{ span: 10 }" :wrapper-col="{ span: 14 }"
        label="Source Types" class="custom-form-item" :rules="[]">
        <span v-for="(option, index) in getSourceTypeOptions(modelRef.category || '', modelRef.style || '')"
          :key="index">
          <span v-if="index == 0">"{{ option.value }}"</span>
          <span v-else>, "{{ option.value }}"</span>
        </span>
      </a-form-item>
      <a-form-item labelAlign="left" labelWrap :label-col="{ span: 10 }" :wrapper-col="{ span: 14 }"
        label="Output Format" v-bind="validateInfos.outputFormat">
        <a-select v-model:value="modelRef.outputFormat" :options="outputFormatOptions"
          placeholder="please select format type">
        </a-select>
      </a-form-item>

      <a-form-item labelAlign="left" labelWrap :label-col="{ span: 10 }" :wrapper-col="{ span: 14 }"
        label="Summary Level" v-bind="validateInfos.summaryLevel">
        <a-select v-model:value="modelRef.summaryLevel" :options="summaryLevelOptions"
          placeholder="please select summary level">
        </a-select>
      </a-form-item>
    </div>
    <div class="menu-item-content">
      <button>Start</button>
    </div>
  </a-form>
</template>

<script lang="ts" src="./FormContentComponent.ts" />
<style lang="css" src="./FormContentStyles.css"></style>
