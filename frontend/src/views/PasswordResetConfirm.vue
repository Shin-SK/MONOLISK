<!-- src/views/PasswordResetConfirm.vue -->
<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api'

const route = useRoute()
const uid = route.query.uid || ''
const token = route.query.token || ''

const form = ref({ new_password1: '', new_password2: '' })
const saving = ref(false)
const done = ref(false)
const errMsg = ref('')

// uid/token が無い場合
const invalid = !uid || !token

async function submit() {
  if (form.value.new_password1 !== form.value.new_password2) {
    errMsg.value = '新しいパスワードが一致しません'
    return
  }
  saving.value = true
  errMsg.value = ''
  try {
    await api.post('dj-rest-auth/password/reset/confirm/', {
      uid,
      token,
      new_password1: form.value.new_password1,
      new_password2: form.value.new_password2,
    }, { cache: false })
    done.value = true
  } catch (e) {
    const d = e?.response?.data
    if (d) {
      const msgs = Object.values(d).flat()
      errMsg.value = msgs.join(' / ') || 'パスワードの再設定に失敗しました'
    } else {
      errMsg.value = e?.message || 'パスワードの再設定に失敗しました'
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="d-flex align-items-center justify-content-center flex-column gap-4 min-vh-100 p-3">
    <img src="/img/logo-full.webp" alt="" style="width: 96px;">
    <div class="container bg-white p-4" style="max-width:420px">

      <template v-if="invalid">
        <h5 class="fw-bold mb-3">無効なリンクです</h5>
        <p class="text-muted small">
          このリンクは無効か、有効期限が切れています。<br>
          もう一度パスワード再設定をお試しください。
        </p>
        <router-link to="/password-reset" class="btn btn-primary w-100">再設定をやり直す</router-link>
      </template>

      <template v-else-if="!done">
        <h5 class="fw-bold mb-3">新しいパスワードを設定</h5>
        <form @submit.prevent="submit" novalidate>
          <div class="mb-3">
            <label class="form-label">新しいパスワード</label>
            <input
              v-model="form.new_password1"
              type="password"
              class="form-control"
              autocomplete="new-password"
              autofocus
            >
          </div>
          <div class="mb-3">
            <label class="form-label">新しいパスワード（確認）</label>
            <input
              v-model="form.new_password2"
              type="password"
              class="form-control"
              autocomplete="new-password"
            >
          </div>
          <div v-if="errMsg" class="alert alert-danger py-1">{{ errMsg }}</div>
          <button type="submit" class="btn btn-primary w-100" :disabled="saving || !form.new_password1 || !form.new_password2">
            {{ saving ? '設定中…' : 'パスワードを設定' }}
          </button>
        </form>
      </template>

      <template v-else>
        <h5 class="fw-bold mb-3">パスワードを再設定しました</h5>
        <p class="text-muted small">新しいパスワードでログインしてください。</p>
        <router-link to="/login" class="btn btn-primary w-100">ログインへ</router-link>
      </template>

      <div v-if="!done" class="mt-3 text-center">
        <router-link to="/login" class="text-decoration-none small">ログインに戻る</router-link>
      </div>
    </div>
  </div>
</template>
