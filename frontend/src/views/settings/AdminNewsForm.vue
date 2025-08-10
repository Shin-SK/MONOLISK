<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { useRoute, useRouter, onBeforeRouteUpdate } from 'vue-router'
import dayjs from 'dayjs'
import { getStoreNotice, createStoreNotice, updateStoreNotice, deleteStoreNotice } from '@/api'


const route  = useRoute()
const router = useRouter()
const rawId = computed(() => route.params.id)
const id    = computed(() => {
  const v = rawId.value
  if (v == null) return 0
  if (typeof v === 'object') return Number(v.id ?? v.pk ?? v.value ?? 0)
  return Number(v)
})
const isEdit = computed(() => Number.isFinite(id.value) && id.value > 0)

const form = reactive({
  title: '',
  body : '',
  is_published: false,
  publish_at  : '',   // datetime-local 用
  pinned: false,
  cover_clear: false,
})

const coverUrl  = ref('')
const coverFile = ref(null)
const loading   = ref(false)

function toDTLocal(v){ return v ? dayjs(v).format('YYYY-MM-DDTHH:mm') : '' }
function toISOorNull(v){ return v ? new Date(v).toISOString() : null }

function onCoverChange(e){
  const f = e.target.files?.[0]
  if (!f) return
  coverFile.value = f
  coverUrl.value  = URL.createObjectURL(f)
  form.cover_clear = false
}
function clearCover(){
  coverFile.value = null
  coverUrl.value  = ''
  form.cover_clear = true
}

async function load(){
  if(!isEdit.value) return
  loading.value = true
  try {
    const d = await getStoreNotice(id.value)
    form.title        = d.title || ''
    form.body         = d.body ?? d.message ?? ''  // 旧データ fallback
    form.is_published = !!d.is_published
    form.publish_at   = toDTLocal(d.publish_at)
    form.pinned       = !!d.pinned
    coverUrl.value    = d.cover_url || ''
  } finally {
    loading.value = false
  }
}

async function save(){
  try {
    const useFormData = !!coverFile.value || !!form.cover_clear
    let payload

    if (useFormData) {
      payload = new FormData()
      payload.append('title', form.title)
      payload.append('body',  form.body)
      payload.append('is_published', String(!!form.is_published))
      if (form.publish_at) payload.append('publish_at', toISOorNull(form.publish_at))
      payload.append('pinned', String(!!form.pinned))
      if (coverFile.value) payload.append('cover', coverFile.value)
	  if (isEdit.value && form.cover_clear) payload.append('cover_clear', 'true')
    } else {
      payload = {
        title: form.title,
        body : form.body,
        is_published: !!form.is_published,
        publish_at  : toISOorNull(form.publish_at),
        pinned: !!form.pinned,
      }
    }
console.warn('[TRACE:form.save] id.value=', id.value, 'typeof=', typeof id.value, 'route.params.id=', route.params.id, 'typeof=', typeof route.params.id)
    const saved = isEdit.value
      ? await updateStoreNotice(id.value, payload)
      : await createStoreNotice(payload)

    alert('保存しました')
    // ← 成功したら一覧へ
    router.push({ name: 'settings-news-list' })
  } catch (e) {
    console.error(e)
    // なるべく詳細を出す
    const d = e?.response?.data
    const msg =
      (typeof d === 'string' && d) ||
      d?.detail ||
      (d && typeof d === 'object'
        ? Object.entries(d).map(([k,v]) => `${k}: ${Array.isArray(v)?v.join(', '):v}`).join('\n')
        : '保存に失敗しました')
    alert(msg)
  }
}


async function removeRow(){
  if (!isEdit.value) return
  if (!confirm('この記事を削除しますか？')) return
  await deleteStoreNotice(id.value)
  router.push({ name: 'settings-news-list' })
}

// 初回 & ルート変更の両方でロード
watch(id, () => { load() }, { immediate: true })
onBeforeRouteUpdate((to, from, next) => { 
  // id が変わるだけの遷移でも確実に再読込
  load().then(() => next())
})
</script>

<template>
  <div class="container-fluid py-4" style="max-width:800px">
    <div class="d-flex align-items-center mb-3">
      <h4 class="m-0">{{ isEdit ? 'お知らせ編集' : 'お知らせ作成' }}</h4>
      <div class="ms-auto d-flex gap-2">
        <RouterLink class="btn btn-outline-secondary" :to="{name:'settings-news-list'}">一覧へ</RouterLink>
        <button v-if="isEdit" class="btn btn-outline-danger" @click="removeRow">削除</button>
        <button class="btn btn-primary" @click="save">保存</button>
      </div>
    </div>

    <div class="card">
      <div class="card-body">
        <div class="mb-3">
          <label class="form-label">タイトル</label>
          <input v-model="form.title" class="form-control" placeholder="タイトル">
        </div>

        <div class="mb-3">
          <label class="form-label">本文</label>
          <textarea v-model="form.body" class="form-control" rows="8" placeholder="本文（改行可）"></textarea>
        </div>

        <div class="row g-3">
          <div class="col-md-6">
            <label class="form-label">公開時刻（空なら即時）</label>
            <input v-model="form.publish_at" type="datetime-local" class="form-control">
          </div>
          <div class="col-md-6 d-flex align-items-end gap-3">
            <div class="form-check">
              <input id="pub" class="form-check-input" type="checkbox" v-model="form.is_published">
              <label for="pub" class="form-check-label">公開する</label>
            </div>
            <div class="form-check">
              <input id="pin" class="form-check-input" type="checkbox" v-model="form.pinned">
              <label for="pin" class="form-check-label">一覧でピン留め</label>
            </div>
          </div>
        </div>

        <div class="mt-4">
          <label class="form-label">カバー画像（1枚）</label>
          <div class="d-flex align-items-center gap-3">
            <img v-if="coverUrl" :src="coverUrl" class="rounded" style="width:160px;height:120px;object-fit:cover;">
            <input type="file" accept="image/*" class="form-control" style="max-width:320px" @change="onCoverChange">
            <button v-if="coverUrl" type="button" class="btn btn-outline-danger btn-sm" @click="clearCover">画像削除</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
