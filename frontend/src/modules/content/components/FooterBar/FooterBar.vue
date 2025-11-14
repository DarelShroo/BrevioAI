<template>
    <a-layout-footer :style="{ textAlign: 'center', height: '64px' }" >
      Generative AI
    </a-layout-footer>
</template>

<style src="./FooterBar.css" scoped >

  
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