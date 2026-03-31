<script setup>
import { ref, computed } from 'vue'
import { api } from '@/api'

const form = ref({ name: '', email: '', body: '', website: '' })
const errors = ref({})
const sending = ref(false)
const done = ref(false)
const serverError = ref('')

const canSubmit = computed(() =>
  form.value.name.trim() && form.value.email.trim() && form.value.body.trim() && !sending.value
)

const submit = async () => {
  errors.value = {}
  serverError.value = ''
  sending.value = true
  try {
    await api.post('accounts/contact/', form.value)
    done.value = true
  } catch (e) {
    if (e.response?.status === 400 && e.response.data) {
      errors.value = e.response.data
    } else if (e.response?.status === 429) {
      serverError.value = '送信回数の上限に達しました。しばらくしてからお試しください。'
    } else {
      serverError.value = '送信に失敗しました。時間をおいて再度お試しください。'
    }
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="d-flex align-items-center justify-content-center flex-column gap-4 min-vh-100 p-3">
    <img src="/img/logo-full.webp" alt="" style="width: 96px;">
    <div class="container bg-white p-4" style="max-width:480px">
      <h5 class="mb-3 fw-bold">お問い合わせ</h5>

      <template v-if="done">
        <div class="alert alert-success">送信しました。ご連絡ありがとうございます。</div>
        <router-link to="/login" class="btn btn-outline-secondary btn-sm">ログイン画面に戻る</router-link>
      </template>

      <form v-else @submit.prevent="submit" novalidate>
        <!-- honeypot -->
        <div style="position:absolute;left:-9999px" aria-hidden="true">
          <input v-model="form.website" tabindex="-1" autocomplete="off">
        </div>

        <div class="mb-3">
          <label class="form-label">お名前 <span class="text-danger">*</span></label>
          <input v-model="form.name" class="form-control" :class="{'is-invalid': errors.name}" maxlength="100">
          <div v-if="errors.name" class="invalid-feedback">{{ errors.name }}</div>
        </div>

        <div class="mb-3">
          <label class="form-label">メールアドレス <span class="text-danger">*</span></label>
          <input v-model="form.email" type="email" class="form-control" :class="{'is-invalid': errors.email}" maxlength="254">
          <div v-if="errors.email" class="invalid-feedback">{{ errors.email }}</div>
        </div>

        <div class="mb-3">
          <label class="form-label">お問い合わせ内容 <span class="text-danger">*</span></label>
          <textarea v-model="form.body" class="form-control" rows="5" :class="{'is-invalid': errors.body}" maxlength="2000"></textarea>
          <div v-if="errors.body" class="invalid-feedback">{{ errors.body }}</div>
        </div>

        <div v-if="serverError" class="alert alert-danger py-1">{{ serverError }}</div>

        <button type="submit" class="btn btn-primary w-100" :disabled="!canSubmit">
          <span v-if="sending" class="spinner-border spinner-border-sm me-1"></span>
          送信
        </button>

        <div class="mt-3 text-center">
          <router-link to="/login" class="text-decoration-none small text-muted">ログイン画面に戻る</router-link>
        </div>
      </form>
    </div>
  </div>
</template>
