<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'

/* ---------- ルーティング ---------- */
const route  = useRoute()
const router = useRouter()
const isEdit = !!route.params.id
const categories  = ref([]) 

/* ---------- フォーム ---------- */
const form = reactive({
  stage_name : '',
  username   : '',
  first_name : '',
  last_name  : '',
  category_rates: [],
  back_rate_free_override       : null,
  back_rate_nomination_override : null,
  back_rate_inhouse_override    : null,
  avatar_clear : false,
})

/* ---------- マスター ---------- */
const stores     = ref([])
const avatarUrl  = ref('')
const avatarFile = ref(null)

function onAvatarChange (e){
  const file = e.target.files[0]
  if (!file) return
  avatarFile.value = file
  avatarUrl.value  = URL.createObjectURL(file)
  form.avatar_clear = false
}
function clearAvatar (){
  avatarFile.value  = null
  avatarUrl.value   = ''
  form.avatar_clear = true
}

/* ---------- バックレート系 ---------- */
async function loadCategories () {
  const { data } = await api.get('billing/item-categories/') // code & name だけでOK
  categories.value = data
}
/* ---------- rate 行を１つ追加 ---------- */
function addRateRow () {
  form.category_rates.push({
    category         : '',   // code をセット
    rate_free        : null,
    rate_nomination  : null,
    rate_inhouse     : null,
  })
}
/* ---------- 行を削除 ---------- */
function removeRateRow (idx){
  form.category_rates.splice(idx,1)
}


// /* ---------- 初期化 ---------- */
async function fetchCast () {
  if (!isEdit) return
  const { data } = await api.get(`billing/casts/${route.params.id}/`)
  Object.assign(form, {
    ...data,
    username   : data.username_read,
    first_name : data.first_name_read,
    last_name  : data.last_name_read,
  })
  avatarUrl.value = data.avatar_url || ''
}

/* ---------- 保存 ---------- */
async function save () {
  try {
    if (!isEdit && !form.username.trim()) {
      alert('ユーザー名を入力してください')
      return
    }

    const body = { ...form }
    let res

    /* multipart か JSON か判定 */
    if (avatarFile.value || form.avatar_clear) {
      const fd = new FormData()
      Object.entries(body).forEach(([k,v])=>{
        if (v !== null && v !== undefined) fd.append(k, v)
      })
      if (avatarFile.value instanceof File) fd.append('avatar', avatarFile.value)
      if (form.avatar_clear) fd.append('avatar_clear', 'true')

      res = isEdit
        ? await api.put(`billing/casts/${route.params.id}/`, fd)
        : await api.post('billing/casts/',                   fd)
    } else {
      res = isEdit
        ? await api.put(`billing/casts/${route.params.id}/`, body)
        : await api.post('billing/casts/',                   body)
    }

    /* 新規登録後は編集モードで残る */
    if (!isEdit) {
      router.replace(`/casts/${res.data.id}`)
      return
    }
    router.push('/casts')
  } catch (e) {
    console.error(e)
    alert(e.response?.data?.detail || '保存に失敗しました')
  }
}

/* ---------- 削除 ---------- */
async function remove () {
  if (!confirm('本当に削除しますか？')) return
  await api.delete(`billing/casts/${route.params.id}/`)
  router.push('/casts')
}

/* ---------- 起動 ---------- */
onMounted(async ()=>{
  await loadCategories()
  await fetchCast()      // 既存キャストは category_rates も流し込み
})
</script>

<template>
<div class="container-fluid py-4" style="max-width:640px">

  <!-- ユーザー名（編集時は readonly） -->
  <div class="mb-3">
    <label class="form-label">ユーザー名</label>
    <input v-model="form.username" class="form-control">
    <small class="text-muted">
      ※ 基本的には変更できしません。変更するとログインIDが変わり、集計等に大きな影響が出ます。
    </small>
  </div>

  <!-- 源氏名 -->
  <div class="mb-3">
    <label class="form-label">源氏名</label>
    <input v-model="form.stage_name" class="form-control">
  </div>


  <!-- 姓名 -->
  <div class="row mb-3">
    <div class="col">
      <label class="form-label">姓</label>
      <input v-model="form.last_name" class="form-control">
    </div>
    <div class="col">
      <label class="form-label">名</label>
      <input v-model="form.first_name" class="form-control">
    </div>
  </div>


  <!-- アバター -->
  <div class="mb-3">
    <label class="form-label">アバター</label>
    <div class="d-flex align-items-center gap-3">
      <img v-if="avatarUrl" :src="avatarUrl" class="rounded"
           style="width:80px;height:80px;object-fit:cover;">
      <input type="file" accept="image/*" @change="onAvatarChange"
             class="form-control" style="max-width:240px;">
      <button v-if="avatarUrl" type="button"
              class="btn btn-outline-danger btn-sm"
              @click="clearAvatar">削除</button>
    </div>
  </div>

  <!-- バック率 -->
  <div class="mb-3">
    <label class="form-label">個別指名等バック率 (%)</label>
    <div class="row g-2">
      <div class="col">
        <input type="number" v-model.number="form.back_rate_free_override"
               placeholder="フリー" class="form-control" min="0" max="100">
      </div>
      <div class="col">
        <input type="number" v-model.number="form.back_rate_nomination_override"
               placeholder="指名" class="form-control" min="0" max="100">
      </div>
      <div class="col">
        <input type="number" v-model.number="form.back_rate_inhouse_override"
               placeholder="場内" class="form-control" min="0" max="100">
      </div>
    </div>
  </div>


  <div class="mb-4">
    <label class="form-label fw-bold">カテゴリ別バック率 (%)</label>
    <table class="table table-sm align-middle">
      <thead class="table-light">
        <tr>
          <th style="width:140px">カテゴリ</th>
          <th>フリー</th><th>本指名</th><th>場内</th><th style="width:60px"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(r,idx) in form.category_rates" :key="idx">
          <!-- ▼カテゴリ選択（code をバインド） -->
          <td>
            <select v-model="r.category" class="form-select form-select-sm">
              <option disabled value="">選択…</option>
              <option v-for="c in categories" :key="c.code" :value="c.code">
                {{ c.name }}
              </option>
            </select>
          </td>
          <td><input v-model.number="r.rate_free"
                    type="number" min="0" max="100" class="form-control form-control-sm"></td>
          <td><input v-model.number="r.rate_nomination"
                    type="number" min="0" max="100" class="form-control form-control-sm"></td>
          <td><input v-model.number="r.rate_inhouse"
                    type="number" min="0" max="100" class="form-control form-control-sm"></td>
          <td class="text-center">
            <button class="btn btn-danger btn-sm"
                    @click="removeRateRow(idx)">✕</button>
          </td>
        </tr>
      </tbody>
    </table>
    <button class="btn btn-outline-secondary btn-sm" @click="addRateRow">
      + 行を追加
    </button>
  </div>

  <!-- 操作ボタン -->
  <div class="d-flex gap-2">
    <button class="btn btn-primary" @click="save">保存</button>
    <button v-if="isEdit" class="btn btn-outline-danger" @click="remove">削除</button>
  </div>

</div>
</template>
