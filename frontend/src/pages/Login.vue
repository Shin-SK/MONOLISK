<template>
	<div class="login-container">
	  <h2>ログイン</h2>
	  <input v-model="username" placeholder="ユーザー名" />
	  <button @click="login">ログイン</button>
	</div>
  </template>
  
  <script setup>
  import { ref } from 'vue';
  import { useRouter } from 'vue-router';
  
  const router = useRouter();
  const username = ref('');
  
  const login = () => {
	if (!username.value) return alert('ユーザー名を入力してください');
  
	// 🔥 超ゆる認証（とりあえず localStorage に保存するだけ）
	localStorage.setItem('user', JSON.stringify({ username: username.value }));
  
	// 🔥 ダッシュボードへリダイレクト
	router.push('/dashboard');
  };
  </script>
  
  <style scoped>
  .login-container {
	text-align: center;
	margin-top: 50px;
  }
  </style>
  