<template>
  <a-menu
    :openKeys="menuBravioStore.openKeys"
    :selectedKeys="selectedKeysArray"
    @update:openKeys="handleOpenKeys"
    @update:selectedKeys="handleSelectedKeys"
    mode="inline"
    :theme="theme"
  >
    <!-- Summary YouTube -->
    <a-sub-menu key="summary-youtube">
      <template #title>
        <AppstoreOutlined />
        <span>Summary YouTube</span>
      </template>
      <a-menu-item key="summary-youtube" class="no-padding border-radius-bottom w-100">
        <div style="padding: 10px;" class="configuration-brevio">
          <a-tabs v-model:activeKey="activeKey">
            <a-tab-pane key="1" tab="Files">
              <div>
                <upload-content-view @update-file-list="updateFileList" :summary-extensions="summaryDocumentsExtension"/>
              </div>
            </a-tab-pane>
            <a-tab-pane key="2" tab="Configuration" force-render>
              <form-content :file-list="fileList" :type-configuration="'summary-youtube'"></form-content>
            </a-tab-pane>
          </a-tabs>
        </div>
      </a-menu-item>

    </a-sub-menu>

    <!-- Summary Media -->
    <a-sub-menu key="summary-media">
      <template #title>
        <AppstoreOutlined />
        <span>Summary Media</span>
      </template>
      <a-menu-item key="summary-media" class="no-padding border-radius-bottom w-100">
        <div style="padding: 10px;" class="configuration-brevio">
          <a-tabs v-model:activeKey="activeKey">
            <a-tab-pane key="1" tab="Files">
              <div>
                <upload-content-view :summary-extensions="summaryDocumentsExtension"/>
              </div>
            </a-tab-pane>
            <a-tab-pane key="2" tab="Configuration" force-render>
              <form-content :type-configuration="'summary-media'"></form-content>
            </a-tab-pane>
          </a-tabs>
        </div>
      </a-menu-item>
    </a-sub-menu>

    <!-- Summary Document -->
    <a-sub-menu key="summary-documents">
      <template #title>
        <AppstoreOutlined />
        <span>Summary Documents</span>
      </template>
      <a-menu-item key="summary-document" class="no-padding border-radius-bottom w-100">
        <div style="padding: 10px;" class="configuration-brevio">
          <a-tabs v-model:activeKey="activeKey">
            <a-tab-pane key="1" tab="Files">
              <div>
                <upload-content-view :summary-extensions="summaryDocumentsExtension"/>
              </div>
            </a-tab-pane>
            <a-tab-pane key="2" tab="Configuration" force-render>
              <form-content :type-configuration="'summary-document'"></form-content>
            </a-tab-pane>
          </a-tabs>
        </div>
      </a-menu-item>
    </a-sub-menu>
  </a-menu>
</template>

<style src="./MenuBar.css" scoped />
<script src="./MenuBar.ts" lang="ts"></script>
