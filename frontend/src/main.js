import { createApp } from 'vue';
import { createPinia } from 'pinia'
import App from './App.vue';
import router from './router';

import '@/assets/scss/main.scss'

createApp(App)
  .use(router)
  .use(createPinia())   // ★ 追加
  .mount('#app')