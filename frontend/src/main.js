// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App    from './App.vue'
import router from './router'
import { setupPWA, restoreRouteIfNeeded } from '@/plugins/pwa'
setupPWA()

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
    restoreRouteIfNeeded(router)
    app.mount('#app')
    installOffcanvasScrollGuard()

// --- スプラッシュ制御 ---
// --- スプラッシュ終了制御（mount後） ---
const EXTRA_MS = 500; // 準備OKからの余白0.5s

const finishSplash = () => {
  // もう表示しようとしているタイマーがあれば止める
  if (window.__splashShowTimer) {
    clearTimeout(window.__splashShowTimer);
    window.__splashShowTimer = null;
  }
  window.__splashDone = true;

  // 本体をふわっと表示
  const appEl = document.getElementById('app');
  appEl?.classList.add('app-shown');
  appEl?.classList.remove('app-hidden');

  // スプラッシュをフェードアウト（出ていなければ出さずに消すでもOK）
  const splash = document.getElementById('splash');
  if (splash) {
    // もしまだvisibleじゃなければ、いきなりhideでもOK
    splash.classList.add('hide');
    splash.addEventListener('transitionend', () => splash.remove(), { once: true });
  }
};

setTimeout(finishSplash, EXTRA_MS);

  
  })()
