/* eslint-disable */
// @ts-nocheck
// Manual ambient typings for app components (PrimeVue is imported explicitly).
export {}

/* prettier-ignore */
declare module 'vue' {
  export interface GlobalComponents {
    AppSidebar: typeof import('./src/components/layout/AppSidebar.vue')['default']
    EstimatePanel: typeof import('./src/components/summary/EstimatePanel.vue')['default']
    FilePicker: typeof import('./src/components/summary/FilePicker.vue')['default']
    RouterLink: typeof import('vue-router')['RouterLink']
    RouterView: typeof import('vue-router')['RouterView']
    StateBlock: typeof import('./src/components/common/StateBlock.vue')['default']
    StatusBadge: typeof import('./src/components/common/StatusBadge.vue')['default']
    SummaryParamsForm: typeof import('./src/components/summary/SummaryParamsForm.vue')['default']
  }
}
