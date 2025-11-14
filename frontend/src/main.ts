import './assets/main.css'
//import {api} from './utils/api'
import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { AppstoreOutlined, SettingOutlined, InboxOutlined } from '@ant-design/icons-vue'
import Antd from 'ant-design-vue'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Antd)
//app.use(api)

app.component('AppstoreOutlined', AppstoreOutlined)
app.component('SettingOutlined', SettingOutlined)
app.component('InboxOutlined', InboxOutlined)

app.mount('#app')
