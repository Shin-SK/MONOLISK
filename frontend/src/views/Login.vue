<!-- frontend/src/views/Login.vue -->
<script setup>
import { ref } from 'vue'
import { useAuth } from '@/stores/useAuth'
import { useRouter, useRoute } from 'vue-router'

const auth   = useAuth()
const router = useRouter()
const route  = useRoute()

const form = ref({ username:'', password:'' })
const err  = ref('')

const submit = async () => {
  err.value = ''
  try {
    await auth.login(form.value.username, form.value.password)
    const next = route.query.next
    router.push(typeof next === 'string' ? next : '/dashboard')
  } catch (e) {
    err.value = 'ユーザー名かパスワードが違います'
  }
}
</script>

<template>
  <div class="d-flex align-items-center justify-content-center">
    <div class="container p-5" style="max-width:420px">
      <h1 class="h4 mb-4 text-center">ログイン</h1>

      <!-- Enter で送信できるよう <form> を使う -->
      <form @submit.prevent="submit" novalidate>
        <div class="mb-3">
          <label class="form-label">ユーザー名</label>
          <input
            v-model="form.username"
            class="form-control"
            autocomplete="username"
            autofocus
          >
        </div>

        <div class="mb-4">
          <label class="form-label">パスワード</label>
          <input
            v-model="form.password"
            type="password"
            class="form-control"
            autocomplete="current-password"
          >
        </div>

        <div v-if="err" class="alert alert-danger py-1">
          {{ err }}
        </div>

        <button type="submit" class="btn btn-primary w-100">
          ログイン
        </button>
      </form>
    </div>
  </div>

</template>
