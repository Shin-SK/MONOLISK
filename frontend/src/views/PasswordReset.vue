<!-- src/views/PasswordReset.vue -->
<script setup>
import { ref } from 'vue'
import { api } from '@/api'

const email = ref('')
const sending = ref(false)
const sent = ref(false)
const errMsg = ref('')

async function submit() {
  sending.value = true
  errMsg.value = ''
  try {
    await api.post('dj-rest-auth/password/reset/', { email: email.value }, { cache: false })
    sent.value = true
  } catch (e) {
    const d = e?.response?.data
    if (d) {
      const msgs = Object.values(d).flat()
      errMsg.value = msgs.join(' / ') || '送信に失敗しました'
    } else {
      errMsg.value = e?.message || '送信に失敗しました'
    }
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="d-flex align-items-center justify-content-center flex-column gap-4 min-vh-100 p-3">
    <img src="/img/logo-full.webp" alt="" style="width: 96px;">
    <div class="container bg-white p-4" style="max-width:420px">

      <template v-if="!sent">
        <h5 class="fw-bold mb-3">パスワード再設定</h5>
        <p class="text-muted small mb-3">
          登録済みのメールアドレスを入力してください。<br>
          パスワード再設定用のメールをお送りします。
        </p>
        <form @submit.prevent="submit" novalidate>
          <div class="mb-3">
            <label class="form-label">メールアドレス</label>
            <input
              v-model="email"
              type="email"
              class="form-control"
              autocomplete="email"
              autofocus
            >
          </div>
          <div v-if="errMsg" class="alert alert-danger py-1">{{ errMsg }}</div>
          <button type="submit" class="btn btn-primary w-100" :disabled="sending || !email">
            {{ sending ? '送信中…' : '再設定メールを送信' }}
          </button>
        </form>
      </template>

      <template v-else>
        <h5 class="fw-bold mb-3">メールを送信しました</h5>
        <p class="text-muted small">
          入力されたメールアドレス宛に、パスワード再設定用のリンクを送信しました。<br>
          メールが届かない場合は、迷惑メールフォルダをご確認ください。
        </p>
      </template>

      <div class="mt-3 text-center">
        <router-link to="/login" class="text-decoration-none small">ログインに戻る</router-link>
      </div>
    </div>
  </div>
</template>
