import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import '@/assets/css/style.scss'


const app = createApp(App);

app.use(router);  // ✅ Vue にルーターを適用
app.mount('#app');  // ✅ `#app` にマウント
