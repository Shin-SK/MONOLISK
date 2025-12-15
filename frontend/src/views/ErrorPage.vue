<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/')
}

const goBack = () => {
  router.back()
}
</script>

<template>
  <div class="d-flex align-items-center justify-content-center flex-column gap-4 min-vh-100 p-3 bg-light">
    <div class="text-center">
      <div style="font-size: 120px; font-weight: bold; color: #dc3545;">⚠️</div>
      <h1 class="mt-4 mb-3">エラーが発生しました</h1>
      <p class="text-muted mb-4" style="font-size: 16px;">
        申し訳ありません。このページへのアクセスは許可されていないか、<br/>
        認証情報が不足しています。
      </p>
    </div>

    <div class="d-flex gap-2">
      <button @click="goHome" class="btn btn btn-primary">
        ホームに戻る
      </button>
      <button @click="goBack" class="btn btn-secondary">
        前のページに戻る
      </button>
    </div>

    <div class="text-muted small mt-4">
      <p>このエラーが繰り返し発生する場合は、ログインし直してください。</p>
    </div>
  </div>
</template>

<style scoped>
</style>
