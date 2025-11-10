<script setup>
import { computed } from 'vue'
import CustomerPicker from './CustomerPicker.vue'

const props = defineProps({
  /** v‑model 開閉 */
  modelValue: Boolean,
  /** 初期表示する顧客 ID（null 可） */
  customerId: Number,
})

const emit = defineEmits([
  'update:modelValue', // 開閉 sync
  'update:customerId', // Picker 内で選択
  'picked',            // 既存客選択
  'saved',             // 保存完了
])

const visible = computed({
  get: () => props.modelValue,
  set: v  => emit('update:modelValue', v),
})

function handlePicked (cust) {
  emit('update:customerId', cust.id)
  emit('picked', cust)
  visible.value = false
}
function handleSaved (cust) {
  emit('update:customerId', cust.id)
  emit('saved', cust)
  visible.value = false
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="modal-backdrop fade show"
      style="z-index:1055;"
    ></div>

    <div
      v-if="visible"
      class="modal fade show"
      style="display:block; z-index:1060;"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <div class="modal-content p-3">
          <div class="modal-header">
            <h5 class="m-0 fw-bold">顧客検索・編集</h5>
            <button class="btn-close" @click="visible = false"></button>
          </div>
          <div class="modal-body">
            <CustomerPicker
              :model-value="customerId"
              @update:modelValue="id => emit('update:customerId', id)"
              @picked="handlePicked"
              @saved="handleSaved"
            />
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
