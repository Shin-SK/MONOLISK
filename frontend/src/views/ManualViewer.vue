<!-- src/views/ManualViewer.vue -->
<script setup>
import { useRouter, useRoute } from 'vue-router'
const router = useRouter()
const route  = useRoute()
const src    = route.query.src || '/manuals/manual-manager.pdf' // フォールバック
function goBack(){ router.back() }
</script>

<template>
  <div class="d-flex flex-column" style="height:100dvh;">
    <div class="border-bottom bg-white d-flex align-items-center gap-2 p-2">
      <button class="btn btn-outline-secondary btn-sm" @click="goBack">← 戻る</button>
      <div class="ms-1 small text-muted text-truncate">PDFビューア</div>
      <a :href="src" target="_blank" rel="noopener" class="ms-auto btn btn-link btn-sm">別タブで開く</a>
    </div>
    <iframe :src="src" style="border:0; flex:1; width:100%;"></iframe>
  </div>
</template>
