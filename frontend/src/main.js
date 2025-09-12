// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App    from './App.vue'
import router from './router'
import './plugins/pwa-auto'
import 'bootstrap';
import { installOffcanvasScrollGuard } from '@/utils/offcanvas-scroll-guard'

import ganttastic from '@infectoone/vue-ganttastic'

import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'

import DatePicker from 'vue-datepicker-next'
import 'vue-datepicker-next/index.css'

import '@/assets/scss/main.scss'
import '@/plugins/dayjs'


import Avatar from '@/components/Avatar.vue' 

import { yen } from '@/utils/money'

import Sortable, { Swap } from 'sortablejs'
Sortable.mount(new Swap())

  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)
  app.use(router)

  .use(ganttastic)
  app.config.globalProperties.$yen = yen
  app.component('Multiselect', Multiselect)  // グローバル登録
  app.component('DatePicker', DatePicker)
  app.component('Avatar', Avatar)

  ;(async () => {
    await router.isReady()
    app.mount('#app')
    installOffcanvasScrollGuard()
  })()
