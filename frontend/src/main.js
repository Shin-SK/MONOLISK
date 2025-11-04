// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App    from './App.vue'
import router from './router'
import { setupPWA, restoreRouteIfNeeded } from '@/plugins/pwa'
setupPWA()

import * as bootstrap from 'bootstrap'
window.bootstrap = bootstrap

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

// ★ 追加：スプラッシュ/更新監視
import { scheduleFinishSplash } from '@/utils/splash'
import { setupUpdateWatcher }   from '@/plugins/update-watcher'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)
  .use(ganttastic)

app.config.globalProperties.$yen = yen
app.component('Multiselect', Multiselect)
app.component('DatePicker', DatePicker)
app.component('Avatar', Avatar)

;(async () => {
  await router.isReady()
  restoreRouteIfNeeded(router)
  app.mount('#app')

  // 起動時に更新チェック → 新版なら「反映中」→ 強制更新
  await setupUpdateWatcher()

  // スプラッシュ終了（通常は500msの余白）
  scheduleFinishSplash(500)
})()
