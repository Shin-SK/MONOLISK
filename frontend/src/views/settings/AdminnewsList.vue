<script setup>
import { ref, onMounted, onActivated } from 'vue'
import dayjs from 'dayjs'
import { listStoreNotices, deleteStoreNotice, updateStoreNotice } from '@/api'

const rows   = ref([])
const q      = ref('')
const status = ref('')         // '', draft, scheduled, published
const pinned = ref('')         // '', '1', '0'
const loading = ref(false)
const error   = ref('')

async function fetchList(){
  loading.value = true
  error.value   = ''
  try {
    const data = await listStoreNotices({
      search: q.value || undefined,
      status: status.value || undefined,
      pinned: pinned.value || undefined,
      ordering: '-pinned,-publish_at,-created_at',
      limit: 50,
    })
  rows.value = data
  } catch (e) {
    error.value = e?.response?.data?.detail || '読み込みに失敗しました'
  } finally {
    loading.value = false
  }
}

function fmt(d){ return d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '—' }

async function togglePublish(r){
  await updateStoreNotice(r.id, { is_published: !r.is_published })
  fetchList()
}
async function togglePinned(r){
  await updateStoreNotice(r.id, { pinned: !r.pinned })
  fetchList()
}
async function removeRow(r){
  if(!confirm(`「${r.title}」を削除しますか？`)) return
  await deleteStoreNotice(r.id)
  fetchList()
}

onMounted(fetchList)
onActivated(fetchList)
</script>

<template>
  <div class="container-fluid py-4">
    <div class="d-flex align-items-center gap-2 mb-3">
      <input v-model="q" class="form-control" style="max-width:260px" placeholder="タイトル/本文 検索" @keyup.enter="fetchList">
      <select v-model="status" class="form-select" style="max-width:160px" @change="fetchList">
        <option value="">すべて</option>
        <option value="draft">下書き</option>
        <option value="scheduled">予約公開</option>
        <option value="published">公開中</option>
      </select>
      <select v-model="pinned" class="form-select" style="max-width:140px" @change="fetchList">
        <option value="">ピン留め: すべて</option>
        <option value="1">ピンのみ</option>
        <option value="0">ピン以外</option>
      </select>
      <button class="btn btn-primary ms-auto" @click="$router.push({name:'settings-news-new'})">新規作成</button>
    </div>

    <div v-if="loading" class="text-muted">読み込み中…</div>
    <div v-else>
      <table class="table align-middle">
        <thead class="table-dark">
          <tr>
            <th>タイトル</th>
            <th style="width:140px" class="text-center">公開</th>
            <th style="width:160px">公開時刻</th>
            <th style="width:100px" class="text-center">ピン</th>
            <th style="width:160px">更新</th>
            <th style="width:180px" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>
              <RouterLink :to="{name:'settings-news-form', params:{id:r.id}}">{{ r.title || '(無題)' }}</RouterLink>
            </td>
            <td class="text-center">
              <span class="badge" :class="r.is_published ? 'bg-success' : 'bg-secondary'">
                {{ r.is_published ? '公開' : '下書き' }}
              </span>
            </td>
            <td>{{ fmt(r.publish_at) }}</td>
            <td class="text-center">
              <span v-if="r.pinned" class="badge bg-warning text-dark">PIN</span>
              <span v-else>—</span>
            </td>
            <td>{{ fmt(r.updated_at) }}</td>
            <td class="text-end">
              <button class="btn btn-outline-secondary btn-sm me-2" @click="togglePinned(r)">
                {{ r.pinned ? 'ピン解除' : 'ピン留め' }}
              </button>
              <button class="btn btn-outline-primary btn-sm me-2" @click="togglePublish(r)">
                {{ r.is_published ? '非公開' : '公開' }}
              </button>
              <button class="btn btn-outline-danger btn-sm" @click="removeRow(r)">削除</button>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="6" class="text-center text-muted">記事がありません</td>
          </tr>
        </tbody>
      </table>

      <div v-if="error" class="alert alert-danger">{{ error }}</div>
    </div>
  </div>
</template>
