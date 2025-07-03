// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App    from './App.vue'
import router from './router'
import 'bootstrap';
import 'bootstrap-icons/font/bootstrap-icons.css'

import ganttastic from '@infectoone/vue-ganttastic'

import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'

import DatePicker from 'vue-datepicker-next'
import 'vue-datepicker-next/index.css'

import '@/assets/scss/main.scss'
import '@/plugins/dayjs'

import { yen } from '@/utils/money'


const app = createApp(App)
  .use(router)
  .use(createPinia())
  .use(ganttastic)
  app.config.globalProperties.$yen = yen
  app.component('Multiselect', Multiselect)  // グローバル登録
  app.component('DatePicker', DatePicker)
app.mount('#app')
