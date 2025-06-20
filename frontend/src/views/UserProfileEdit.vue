<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/api'

const form = ref({ display_name: '', avatar: null })

onMounted(async () => {
  form.value = await api.get('dj-rest-auth/user/').then(r => r.data)
})

const fileInput = e => (form.value.avatar = e.target.files[0])

async function save () {
  const fd = new FormData()
  fd.append('display_name', form.value.display_name)
  if (form.value.avatar instanceof File) fd.append('avatar', form.value.avatar)

  await api.patch('dj-rest-auth/user/', fd,
    { headers:{ 'Content-Type':'multipart/form-data' } })
  alert('更新しました')
}
</script>

<template>
  <div class="container py-4">
    <h1 class="h4">プロフィール編集</h1>

    <div class="mb-3">
      <label class="form-label">表示名</label>
      <input v-model="form.display_name" class="form-control">
    </div>

    <div class="mb-3">
      <label class="form-label">アイコン</label>
      <input type="file" accept="image/*" @change="fileInput" class="form-control">
      <img v-if="form.avatar && typeof form.avatar==='string'" :src="form.avatar" class="mt-2 rounded" width="96">
    </div>

    <button class="btn btn-primary" @click="save">保存</button>
  </div>
</template>
