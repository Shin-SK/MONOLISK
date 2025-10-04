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
  hourly_wage: null,
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
    hourly_wage: data.hourly_wage,
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

    if (!isEdit) {
      body.username_in   = (form.username || '').trim()
      body.first_name_in = form.first_name || ''
      body.last_name_in  = form.last_name || ''
    } else {
      // 変更しないなら username は送らない（誤更新防止）
      delete body.username
      delete body.first_name_in
      delete body.last_name_in
      // もし編集でユーザー名を変更したいときだけ：
      // body.username_in = (form.username || '').trim()
    }

    let res

    if (avatarFile.value || form.avatar_clear) {
      // ---- multipart（画像 or クリアあり）----
      const fd = new FormData()
      // primitives
      for (const [k, v] of Object.entries(body)) {
        if (k === 'category_rates') continue           // ← ここは別で JSON 化
        if (v !== null && v !== undefined) fd.append(k, v)
      }
      // nested 配列は JSON で送る
      fd.append('category_rates', JSON.stringify(form.category_rates || []))

      if (avatarFile.value instanceof File) fd.append('avatar', avatarFile.value)
      if (form.avatar_clear) fd.append('avatar_clear', 'true')

      res = isEdit
        ? await api.put(`billing/casts/${route.params.id}/`, fd)
        : await api.post('billing/casts/', fd)
    } else {
      // ---- JSON ----
      res = isEdit
        ? await api.put(`billing/casts/${route.params.id}/`, body)
        : await api.post('billing/casts/', body)
    }

    // 遷移（名前付きルート）
    if (!isEdit) {
      router.replace({ name: 'settings-cast-form', params: { id: res.data.id } })
    } else {
      router.push({ name: 'settings-cast-list' })
    }
  } catch (e) {
    console.error(e)
    alert(e.response?.data?.detail || '保存に失敗しました')
  }
}


/* ---------- 削除 ---------- */
async function remove () {
  if (!confirm('本当に削除しますか？')) return
  await api.delete(`billing/casts/${route.params.id}/`)
  router.push({ name: 'settings-cast-list' })   // ← ここだけ変更
}

/* ---------- 起動 ---------- */
onMounted(async ()=>{
  await loadCategories()
  await fetchCast()      // 既存キャストは category_rates も流し込み
})
</script>

<template>
  <div
    class="container-fluid py-4"
  >
    <!-- ユーザー名（編集時は readonly） -->
    <div class="mb-3">
      <label class="form-label">ユーザー名</label>
      <input
        v-model="form.username"
        class="form-control"
      >
      <small class="text-muted">
        ※ 基本的には変更できしません。変更するとログインIDが変わり、集計等に大きな影響が出ます。
      </small>
    </div>

    <!-- 源氏名 -->
    <div class="mb-3">
      <label class="form-label">源氏名</label>
      <input
        v-model="form.stage_name"
        class="form-control"
      >
    </div>


    <!-- 姓名 -->
    <div class="row mb-3">
      <div class="col">
        <label class="form-label">姓</label>
        <input
          v-model="form.last_name"
          class="form-control"
        >
      </div>
      <div class="col">
        <label class="form-label">名</label>
        <input
          v-model="form.first_name"
          class="form-control"
        >
      </div>
    </div>


    <!-- アバター -->
    <div class="mb-3">
      <label class="form-label">アバター</label>
      <div class="d-flex flex-column flex-md-row gap-3">
        <img
          v-if="avatarUrl"
          :src="avatarUrl"
          class="rounded"
          style="width:80px;height:80px;object-fit:cover;"
        >
        <div class="wrap d-flex align-items-center gap-2">
          <input
            type="file"
            accept="image/*"
            class="form-control"
            style="max-width:240px;"
            @change="onAvatarChange"
          >
          <button
            v-if="avatarUrl"
            type="button"
            class="btn btn-outline-danger btn-sm"
            @click="clearAvatar"
          >
            削除
          </button>
        </div>
      </div>
    </div>

    <div class="mb-3">
      <label class="form-label">時給 (円)</label>
      <input
        v-model.number="form.hourly_wage"
        type="number"
        class="form-control"
        min="0"
        placeholder="例: 3000"
      >
    </div>

    <!-- バック率 -->
    <div class="mb-3">
      <label class="form-label">個別指名等バック率 (%)</label>
      <div class="row g-2">
        <div class="col">
          <input
            v-model.number="form.back_rate_free_override"
            type="number"
            placeholder="フリー"
            class="form-control"
            min="0"
            max="100"
          >
        </div>
        <div class="col">
          <input
            v-model.number="form.back_rate_nomination_override"
            type="number"
            placeholder="指名"
            class="form-control"
            min="0"
            max="100"
          >
        </div>
        <div class="col">
          <input
            v-model.number="form.back_rate_inhouse_override"
            type="number"
            placeholder="場内"
            class="form-control"
            min="0"
            max="100"
          >
        </div>
      </div>
    </div>


    <div class="mb-4">
      <label class="form-label fw-bold">カテゴリ別バック率 (%)</label>
      <div class="table-responsive">
        <table class="table table-sm align-middle" style="min-width: 480px;">
          <thead class="table-light">
            <tr>
              <th style="width:140px">
                カテゴリ
              </th>
              <th>フリー</th><th>本指名</th><th>場内</th><th style="width:60px" />
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(r,idx) in form.category_rates"
              :key="idx"
            >
              <!-- ▼カテゴリ選択（code をバインド） -->
              <td>
                <select
                  v-model="r.category"
                  class="form-select form-select-sm"
                >
                  <option
                    disabled
                    value=""
                  >
                    選択…
                  </option>
                  <option
                    v-for="c in categories"
                    :key="c.code"
                    :value="c.code"
                  >
                    {{ c.name }}
                  </option>
                </select>
              </td>
              <td>
                <input
                  v-model.number="r.rate_free"
                  type="number"
                  min="0"
                  max="100"
                  class="form-control form-control-sm"
                >
              </td>
              <td>
                <input
                  v-model.number="r.rate_nomination"
                  type="number"
                  min="0"
                  max="100"
                  class="form-control form-control-sm"
                >
              </td>
              <td>
                <input
                  v-model.number="r.rate_inhouse"
                  type="number"
                  min="0"
                  max="100"
                  class="form-control form-control-sm"
                >
              </td>
              <td class="text-center">
                <button
                  class="btn btn-danger btn-sm"
                  @click="removeRateRow(idx)"
                >
                  ✕
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <button
        class="btn btn-outline-secondary btn-sm"
        @click="addRateRow"
      >
        + 行を追加
      </button>
    </div>

    <!-- 操作ボタン -->
    <div class="d-flex gap-2">
      <button
        class="btn btn-primary"
        @click="save"
      >
        保存
      </button>
      <button
        v-if="isEdit"
        class="btn btn-outline-danger"
        @click="remove"
      >
        削除
      </button>
    </div>
  </div>
</template>


<style scoped>
input{
  background-color: white;
}

</style>