// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App    from './App.vue'
import router from './router'
import ganttastic from '@infectoone/vue-ganttastic'

import '@/assets/scss/main.scss'
import '@/plugins/dayjs'

createApp(App)
  .use(router)
  .use(createPinia())
  .use(ganttastic)
  .mount('#app')
