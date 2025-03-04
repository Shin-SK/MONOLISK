import { createApp } from 'vue';
import App from './App.vue';
import router from './router';

const app = createApp(App);

app.use(router);  // ✅ Vue にルーターを適用
app.mount('#app');  // ✅ `#app` にマウント
