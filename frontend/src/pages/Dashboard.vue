<template>
	<div class="dashboard">
	  <h2>ダッシュボード</h2>
    <p v-if="user">ようこそ, {{ user.username }} さん</p>
	  <button @click="logout">ログアウト</button>
	</div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue';
  import { useRouter } from 'vue-router';

  const router = useRouter();
  const user = ref(null);  // ✅ 初期値を null にする

  // ✅ 仮のデータをセット（本当はAPIから取得）
  setTimeout(() => {
  user.value = { username: 'hoge', email: 'hoge@example.com' };
  }, 1000);  

  
  onMounted(() => {
	const storedUser = localStorage.getItem('user');
	if (!storedUser) {
	  router.push('/login');
	} else {
	  user.value = JSON.parse(storedUser);
	}
  });
  
  const logout = () => {
	localStorage.removeItem('user');
	router.push('/login');
  };
  </script>
  
  <style scoped>
  .dashboard {
	text-align: center;
	margin-top: 50px;
  }
  </style>
  