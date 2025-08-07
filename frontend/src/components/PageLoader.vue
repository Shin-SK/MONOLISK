<!-- src/components/PageLoader.vue -->
<script setup>
import { ref, watch } from 'vue'

/* 親から on/off を受け取るだけ */
const props = defineProps({ active: Boolean })

/* 0.5 s 後にスピナーを表示 */
const showSpinner = ref(false)
let timer

watch(
  () => props.active,
  (val) => {
    clearTimeout(timer)
    if (val) {
      timer = setTimeout(() => (showSpinner.value = true), 1000)
    } else {
      showSpinner.value = false
    }
  },
  { immediate: true }
)
</script>

<template>
  <!-- DOM は常駐。CSS で表示／非表示を切替 -->
  <div
    class="loader position-absolute top-0 start-0 w-100 h-100
           d-flex justify-content-center align-items-center"
    :class="props.active ? 'show' : 'hide'"
  >
    <span v-show="showSpinner" class="spinner" />
  </div>
</template>

<style scoped>
/* ───────── 背景 ───────── */
.loader {
  z-index: 10;
  background: #f7f7f7;
  /* デフォルトは即表示（transition なし） */
  transition: none;
}
/* 非表示になるときだけフェードアウトさせる */
.loader.hide {
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
}
/* 表示状態はそのまま不透明 */
.loader.show {
  opacity: 1;
}

/* ───────── スピナー ───────── */
.spinner {
  width: 50px;
  aspect-ratio: 1;
  color: #000;
  background: currentColor;
  border-radius: 50%;
  position: relative;
}
.spinner:before {
  content: '';
  position: absolute;
  background:
    radial-gradient(farthest-side at bottom right, #0000 94%, currentColor 96%) 0 0,
    radial-gradient(farthest-side at bottom left , #0000 94%, currentColor 96%) 100% 0,
    radial-gradient(farthest-side at top    left , #0000 94%, currentColor 96%) 100% 100%,
    radial-gradient(farthest-side at top    right, #0000 94%, currentColor 96%) 0 100%;
  background-size: 25px 25px;
  background-repeat: no-repeat;
  animation: l39-1 1s infinite, l39-2 1s infinite;
}
@keyframes l39-1 {
  0%,10%,90%,100% { inset: 0 }
  40%,60%         { inset: -10px }
}
@keyframes l39-2 {
  0%,40%  { transform: rotate(0) }
  60%,100%{ transform: rotate(90deg) }
}
</style>
