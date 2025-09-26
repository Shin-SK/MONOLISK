<!-- components/BaseModal.vue -->
<script setup>
import { Teleport, watch, onBeforeUnmount } from 'vue'
defineOptions({ inheritAttrs: false })

const props = defineProps({ modelValue: Boolean })
const emit  = defineEmits(['update:modelValue'])
const close = () => emit('update:modelValue', false)

// 背景スクロールロック
let _lockedY = 0
const lockBody = () => {
	// すでにロック済みなら何もしない
	if (document.body.classList.contains('modal-open')) return
	_lockedY = window.scrollY || document.documentElement.scrollTop || 0

	// スクロールバー幅ぶんの右パディングでレイアウトのズレを防ぐ
	const scrollbarW = window.innerWidth - document.documentElement.clientWidth
	if (scrollbarW > 0) document.body.style.paddingRight = `${scrollbarW}px`

	document.body.classList.add('modal-open')
	document.body.style.position = 'fixed'
	document.body.style.top = `-${_lockedY}px`
	document.body.style.width = '100%'
	document.body.style.overflow = 'hidden'
}
const unlockBody = () => {
	if (!document.body.classList.contains('modal-open')) return
	document.body.classList.remove('modal-open')
	document.body.style.position = ''
	document.body.style.top = ''
	document.body.style.width = ''
	document.body.style.overflow = ''
	document.body.style.paddingRight = ''
	// 元のスクロール位置へ復帰
	window.scrollTo(0, _lockedY || 0)
}

watch(() => props.modelValue, v => (v ? lockBody() : unlockBody()), { immediate: true })
onBeforeUnmount(unlockBody)
</script>

<template>
  <Teleport to="body">
    <!-- backdrop -->
    <transition name="backdrop-fade">
      <div v-if="modelValue" class="modal-backdrop" @click="close" />
    </transition>

    <!-- modal 本体 -->
    <transition name="modal-fade">
      <div
        v-if="modelValue"
        class="modal d-block"
        role="dialog"
        @keydown.esc="close"
        v-bind="$attrs"
      >
        <div class="modal-dialog modal-dialog-scrollable modal-fullscreen p-3">
          <div class="modal-content">
            <!-- ヘッダー -->
            <slot name="header" />

            <div class="modal-body d-flex p-3">
              <slot />
            </div>

            <!-- フッター -->
            <slot name="footer">
              <div class="modal-footer" />
            </slot>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style>
/* body は scoped外で当てる */
body.modal-open { overflow: hidden; touch-action: none; }
</style>

<style scoped>
/* ---------- ベース ---------- */
.modal-backdrop{
  position:fixed; inset:0;
  background:#000; opacity:.5;
  z-index:1050;
}
.modal{ z-index:1055; }   /* backdrop より前面 */

/* ---------- フェード効果 ---------- */
.backdrop-fade-enter-active,
.backdrop-fade-leave-active{transition:opacity .3s ease;}
.backdrop-fade-enter-from,
.backdrop-fade-leave-to  {opacity:0;}

.modal-fade-enter-active,
.modal-fade-leave-active{transition:opacity .3s ease, transform .3s ease;}
.modal-fade-enter-from,
.modal-fade-leave-to  {opacity:0; transform:scale(.98);}
</style>
