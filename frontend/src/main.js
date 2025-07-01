// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App    from './App.vue'
import router from './router'
import ganttastic from '@infectoone/vue-ganttastic'

import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'

import DatePicker from 'vue-datepicker-next'
import 'vue-datepicker-next/index.css'

import '@/assets/scss/main.scss'
import '@/plugins/dayjs'


const app = createApp(App)
  .use(router)
  .use(createPinia())
  .use(ganttastic)

  app.component('Multiselect', Multiselect)  // グローバル登録
  app.component('DatePicker', DatePicker)
app.mount('#app')
