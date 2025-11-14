<template>
  <div v-show="!loading" class="container-bravio" :style="{ backgroundImage: `url(${backgroundImage})` }">
    <!--          <div
            v-show="!loading && !isUserSearched"
            id="container-config-search"
            class="container-bravio"
            :style="{
              margin: 0,
              padding: 0,
              boxSizing: 'border-box',
              display: 'flex',
              flexDirection: 'row',
              width: '100%',
            }"
          >
            <menu-bar />
            <div class="container-config">
              <div class="config-element-selected">
                <div v-text="selectedKeysNames[useMenuBravio.combinedSelectedKeys[0]]"></div>
              </div>
              <div class="container-config mt-20px search-bar">
                <search-bar
                  v-model:loading="loading"
                  v-model:isUserSearched="isUserSearched"
                  v-model:error="error"
                  v-model:result_content="result_content"
                  @update:loading="handleLoadingUpdate"
                  @update:isUserSearched="handleisUserSearchedUpdate"
                  @update:error="handleisErrorUpdate"
                  @update:result_content="handlResultContentUpdate"
                />
              </div>
              <div style="" class="container-config config-box">
                <Suspense>
                  <config-box />
                </Suspense>
              </div>
            </div>
          </div>
          <div
            v-show="!loading && isUserSearched"
            id="container-config-search"
            style="width: 100%; padding: 10px 10px 5px 10px"
          >
            <div style="background-color: white; height: 400px; margin-bottom: 10px">
              <p v-text="result_content">
              </p>

            </div>
            <div
              style="
                height: 25px;
                width: 100%;
                align-items: center;
                align-content: center;
                justify-content: space-between;
                display: flex;
              "
            >

              <a-button type="primary" style="width: 120px; text-align: center">Previous</a-button>
              <a-button type="primary" style="width: 120px; text-align: center">Next</a-button>
            </div>
          </div>-->
          <div
            v-show="!loading && !isUserSearched"
            id="container-config-search"
            class="container-bravio"
            :style="{
              margin: 0,
              padding: 0,
              boxSizing: 'border-box',
              display: 'flex',
              flexDirection: 'row',
              width: '100%',
            }"
          >
            <menu-bar />

          </div>
          <div
            v-show="!loading && isUserSearched"
            id="container-config-search"
            style="width: 100%; padding: 10px 10px 5px 10px"
          >
            <div style="background-color: white; height: 400px; margin-bottom: 10px">
              <p v-text="result_content">
              </p>

            </div>
            <div
              style="
                height: 25px;
                width: 100%;
                align-items: center;
                align-content: center;
                justify-content: space-between;
                display: flex;
              "
            >

              <a-button type="primary" style="width: 120px; text-align: center">Previous</a-button>
              <a-button type="primary" style="width: 120px; text-align: center">Next</a-button>
            </div>
          </div>
  </div>
</template>

<script lang="ts" src="./ContentBrevio.ts" />

<style src="./ContentBrevio.css" scoped />
