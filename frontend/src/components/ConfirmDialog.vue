<script setup>
import { Teleport } from 'vue'

defineProps({
  modelValue: Boolean,
  message: { type: String, default: '' },
  okLabel: { type: String, default: 'はい' },
  cancelLabel: { type: String, default: 'いいえ' },
})
const emit = defineEmits(['update:modelValue', 'ok', 'cancel'])

function onOk() { emit('ok'); emit('update:modelValue', false) }
function onCancel() { emit('cancel'); emit('update:modelValue', false) }
</script>

<template>
  <Teleport to="body">
    <transition name="cd-fade">
      <div v-if="modelValue" class="cd-overlay" @click.self="onCancel">
        <div class="cd-box">
          <div class="cd-body">{{ message }}</div>
          <div class="cd-actions">
            <button class="btn btn-outline-secondary btn-sm" @click="onCancel">{{ cancelLabel }}</button>
            <button class="btn btn-primary btn-sm" @click="onOk">{{ okLabel }}</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.cd-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.45);
  z-index: 1070;
  display: flex; align-items: center; justify-content: center;
}
.cd-box {
  background: #fff; border-radius: 10px;
  padding: 1.5rem; min-width: 280px; max-width: 90vw;
  box-shadow: 0 4px 24px rgba(0,0,0,.2);
}
.cd-body { font-size: 1rem; margin-bottom: 1.2rem; text-align: center; }
.cd-actions { display: flex; gap: .6rem; justify-content: center; }
.cd-actions .btn { min-width: 80px; }
.cd-fade-enter-active, .cd-fade-leave-active { transition: opacity .2s ease; }
.cd-fade-enter-from, .cd-fade-leave-to { opacity: 0; }
</style>
