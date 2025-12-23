<script setup>
import { ref, nextTick } from 'vue'
import { useAuth } from '@/stores/useAuth'
import { useRouter, useRoute } from 'vue-router'

const auth   = useAuth()
const router = useRouter()
const route  = useRoute()

const form = ref({ username:'', password:'' })
const err  = ref('')

// ★追加：パスワード表示切替
const showPassword = ref(false)
const passwordRef = ref(null)

const togglePassword = async () => {
  showPassword.value = !showPassword.value
  await nextTick()
  // フォーカス維持（地味にUX良い）
  passwordRef.value?.focus?.()
}

const submit = async () => {
  err.value = ''
  try {
    await auth.login(form.value.username, form.value.password)
    await router.replace('/')
  } catch (e) {
    err.value = 'ユーザー名かパスワードが違います'
  }
}
</script>

<template>
  <div class="d-flex align-items-center justify-content-center flex-column gap-4 min-vh-100 p-3">
    <img src="/img/logo-full.webp" alt="" style="width: 96px;">
    <div class="container bg-white p-4" style="max-width:420px">
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
          <div class="wrap position-relative">
            <input
              ref="passwordRef"
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              class="form-control"
              autocomplete="current-password"
            >
            <button
              type="button"
              class="btn btn-sm text-secondary position-absolute top-50 end-0 translate-middle-y me-2 p-1"
              @click="togglePassword"
              :aria-label="showPassword ? 'パスワードを隠す' : 'パスワードを表示'"
              :title="showPassword ? '隠す' : '表示'"
            >
              <IconEye v-if="!showPassword" />
              <IconEyeOff v-else />
            </button>
          </div>
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