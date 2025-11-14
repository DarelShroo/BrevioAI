<template>
  <div style="padding: 20px;">
    <a-upload-dragger
      :key="fileList.length"
      class="upload-dragger"
      v-model:fileList="fileList"
      name="file"
      :multiple="true"
      :customRequest="dummyRequest"
      :showUploadList="true"
      @change="handleChange"
      @drop="handleDrop"
      :accept="summaryExtensions"
    >
      <div class="container-upload-content">
        <p class="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p class="ant-upload-text">
          Click or drag file to this area to upload
        </p>
        <p class="ant-upload-hint">
          Support for a single or bulk upload. Strictly prohibit from uploading
          company data or other banned files.
        </p>
      </div>
    </a-upload-dragger>
  </div>
</template>

<script lang="ts" src="./UploadContent.ts"></script>
<style lang="css" src="./UploadContent.css"></style>
