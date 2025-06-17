<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createCustomer, updateCustomer, deleteCustomer, getCustomer } from '@/api'

const route   = useRoute()
const router  = useRouter()
const isEdit  = !!route.params.id

const form = ref({ name:'', phone:'', address:'', memo:'' })

/* 編集モードなら既存データ取得 */
onMounted(async () => {
  if (!isEdit) return
	const data = await getCustomer(route.params.id)      // ←完全一致取得
	Object.assign(form.value, data)
})

async function save() {
  try {
    if (isEdit)
      await updateCustomer(route.params.id, form.value)
    else
      await createCustomer(form.value)
    router.push('/customers')
  } catch(e) {
    alert(e.response?.data?.detail || '保存に失敗しました')
  }
}

async function remove() {
  if (!confirm('削除しますか？')) return
  await deleteCustomer(route.params.id)
  router.push('/customers')
}
</script>

<template>
<div class="container py-4" style="max-width:560px">
  <h1 class="h4 mb-3">{{ isEdit ? '顧客編集' : '顧客登録' }}</h1>

  <div class="mb-3">
    <label class="form-label">名前</label>
    <input v-model="form.name" class="form-control">
  </div>

  <div class="mb-3">
    <label class="form-label">電話番号</label>
    <input v-model="form.phone" class="form-control">
  </div>

  <div class="mb-3">
    <label class="form-label">住所</label>
    <input v-model="form.address" class="form-control">
  </div>

  <div class="mb-3">
    <label class="form-label">メモ</label>
    <textarea v-model="form.memo" rows="3" class="form-control"></textarea>
  </div>

  <div class="d-flex justify-content-between">
    <button class="btn btn-secondary" @click="$router.back()">戻る</button>
    <div>
      <button v-if="isEdit" class="btn btn-outline-danger me-2" @click="remove">削除</button>
      <button class="btn btn-primary" @click="save">保存</button>
    </div>
  </div>
</div>
</template>
