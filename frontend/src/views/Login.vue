<script setup>
import { ref }     from 'vue'
import { useAuth } from '@/stores/useAuth'
import { useRouter } from 'vue-router'

const auth   = useAuth()
const router = useRouter()

const form = ref({ username:'', password:'' })
const err  = ref('')

const submit = async () => {
  err.value = ''
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/')               // ← ログイン後に元ページへ跳ばすなら要カスタム
  } catch (e) {
    err.value = 'ユーザー名かパスワードが違います'
  }
}
</script>

<template>
  <div class="container py-5" style="max-width:420px">
    <h1 class="h4 mb-4 text-center">ログイン</h1>

    <div class="mb-3">
      <label class="form-label">ユーザー名</label>
      <input v-model="form.username" class="form-control" autocomplete="username" />
    </div>

    <div class="mb-4">
      <label class="form-label">パスワード</label>
      <input v-model="form.password" type="password"
             class="form-control" autocomplete="current-password" />
    </div>

    <div v-if="err" class="alert alert-danger py-1">{{ err }}</div>

    <button class="btn btn-primary w-100" @click="submit">ログイン</button>
  </div>
</template>
