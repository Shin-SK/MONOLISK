<!-- components/BaseModal.vue -->
<script setup>
import { Teleport } from 'vue'
defineOptions({ inheritAttrs: false })
const props = defineProps({ modelValue: Boolean })
const emit  = defineEmits(['update:modelValue'])
const close = () => emit('update:modelValue', false)
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
        <div class="modal-dialog modal-dialog-scrollable modal-fullscreen p-md-5 p-3">
          <div class="modal-content">
            <!-- ヘッダー -->
            <slot name="header" />

            <!-- ★ ここを .modal-body にする -->
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


<style scoped>
/* ---------- ベース ---------- */
.modal-backdrop{
  position:fixed; inset:0;
  background:#000; opacity:.5;
  z-index:1050;
}
.modal{ z-index:1055; }   /* backdrop より前面 */

/* ---------- フェード効果 ---------- */
/* backdrop */
.backdrop-fade-enter-active,
.backdrop-fade-leave-active{transition:opacity .3s ease;}
.backdrop-fade-enter-from,
.backdrop-fade-leave-to  {opacity:0;}

/* modal */
.modal-fade-enter-active,
.modal-fade-leave-active{transition:opacity .3s ease, transform .3s ease;}
.modal-fade-enter-from,
.modal-fade-leave-to  {opacity:0; transform:scale(.98);}
</style>