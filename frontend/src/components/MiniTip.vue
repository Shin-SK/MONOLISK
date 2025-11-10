<!-- src/components/MiniTip.vue -->
<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },  // v-model で開閉
  text:       { type: String,  default: '' },     // 表示テキスト
  align:      { type: String,  default: 'right' } // right|left|center
})
const emit = defineEmits(['update:modelValue'])

const root = ref(null)

function close(){ emit('update:modelValue', false) }

function onDocClick(e){
  if (!root.value) return
  if (!root.value.contains(e.target)) close()
}

onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div ref="root" class="mini-tip-root">
    <slot /> <!-- トリガ（ボタン等）をここに -->

    <transition name="fade">
      <div
        v-if="modelValue"
        class="mini-tip-badge"
        :data-align="align"
        role="tooltip"
      >
        <slot name="text">{{ text }}</slot>
        <span class="mini-tip-arrow" />
      </div>
    </transition>
  </div>
</template>

<style scoped>
.mini-tip-root{ position: relative; display:inline-flex; align-items:center; }

.mini-tip-badge{
  position:absolute;
  top: calc(100% + 6px);
  background: rgba(0,0,0,.85);
  color:#fff;
  font-size:.75rem;
  padding:.3rem .5rem;
  border-radius:.375rem;
  white-space:nowrap;
  z-index: 1000;
  box-shadow:0 4px 12px rgba(0,0,0,.15);
}
.mini-tip-badge[data-align="right"]  { right:.5rem; }
.mini-tip-badge[data-align="left"]   { left:.5rem; }
.mini-tip-badge[data-align="center"] { left:50%; transform:translateX(-50%); }

.mini-tip-arrow{
  position:absolute; top:-6px; right:.75rem;
  width:0;height:0;border:6px solid transparent;
  border-bottom-color:rgba(0,0,0,.85);
}
.mini-tip-badge[data-align="left"]  .mini-tip-arrow{ right:auto; left:.75rem; }
.mini-tip-badge[data-align="center"] .mini-tip-arrow{ left:50%; transform:translateX(-50%); }

.fade-enter-active,.fade-leave-active{ transition:opacity .15s ease; }
.fade-enter-from,.fade-leave-to{ opacity:0; }
</style>
