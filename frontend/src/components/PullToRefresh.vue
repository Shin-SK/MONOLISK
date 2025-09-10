<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({ threshold: { type: Number, default: 64 } }) // 更新発火の引き量px
const emit  = defineEmits(['refresh'])

const wrap = ref(null)
const pulling = ref(false)
const ready = ref(false)
const offset = ref(-8)
let startY = 0
let tracking = false

function onStart(e){
  if (!wrap.value) return
  if (wrap.value.scrollTop > 0) return
  startY = e.touches[0].clientY
  tracking = true
}
function onMove(e){
  if (!tracking) return
  const dy = e.touches[0].clientY - startY
  if (dy > 0 && wrap.value.scrollTop <= 0){
    // ブラウザのデフォルトスクロールを止める
    e.preventDefault()
    offset.value = Math.min(dy / 2, props.threshold * 1.5)
    pulling.value = true
    ready.value = offset.value >= props.threshold
  }else{
    // 逆方向に動いたら“静かに”元へ（連続resetでチラつかせない）
    pulling.value = false
    ready.value = false
    offset.value = 8
    tracking = false
  }
}
async function onEnd(){
  if (!pulling.value) return reset()
  if (ready.value){
    await emit('refresh')
  }
  reset()
}
function reset(){
  pulling.value = false
  ready.value = false
  offset.value = 8
  tracking = false
}

onMounted(()=>{
  const el = wrap.value
  el.addEventListener('touchstart', onStart, { passive: true })
  el.addEventListener('touchmove',  onMove,  { passive: false })
  el.addEventListener('touchend',   onEnd,   { passive: true })
})
onUnmounted(()=>{
  const el = wrap.value
  if(!el) return
  el.removeEventListener('touchstart', onStart)
  el.removeEventListener('touchmove',  onMove)
  el.removeEventListener('touchend',   onEnd)
})
</script>

<template>
  <div ref="wrap" class="ptr-wrap" :style="{ '--ptr-offset': offset + 'px' }">
    <div class="ptr-indicator" :style="{ height: pulling ? '48px' : '0px' }">
      <span v-if="!ready">↓ 引いて更新</span>
      <span v-else>離して更新</span>
    </div>
    <div class="ptr-content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.ptr-wrap {
  --ptr-offset: 8px;                 /* ここが唯一の真実 */
  height: 100vh;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-y: contain;
  touch-action: pan-y;               /* iOS/Androidで縦操作を明示 */
}
.ptr-indicator {
  display:flex; align-items:center; justify-content:center;
  color:#666; transition: height .2s ease;
  transform: translate3d(0, var(--ptr-offset), 0) !important;
}
.ptr-content {
  padding-top: var(--ptr-offset);
}

</style>
