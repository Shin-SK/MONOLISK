<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'

const route   = useRoute()
const router  = useRouter()
const isEdit  = !!route.params.id

/* ------------- フォーム ---------------- */
const form = ref({
  user:'', store:'',
  phone:'', car_type:'', memo:'', number:'',
  ng_casts:[],
})

/* ------------- マスター ---------------- */
const stores = ref([])
const casts  = ref([])

/* NG キャスト検索 */
const kw = ref('')
const cand = ref([])
const showCand = ref(false)

async function searchCast() {
  if (kw.value.length < 2) { showCand.value = false; return }
  cand.value = await api.get('cast-profiles/', { params:{ search: kw.value } })
                       .then(r=>r.data)
  showCand.value = cand.value.length > 0
}
function addNg(c) {
  if (!form.value.ng_casts.includes(c.id))
    form.value.ng_casts.push(c.id)
  kw.value=''; showCand.value=false
}
function removeNg(id){
  form.value.ng_casts = form.value.ng_casts.filter(x=>x!==id)
}

/* ------------- CRUD ---------------- */
async function fetchMasters(){
  const [st, cs] = await Promise.all([
    api.get('stores/').then(r=>r.data),
    api.get('cast-profiles/').then(r=>r.data),
  ])
  ;[stores.value, casts.value] = [st, cs]
}
async function fetchDriver(){
  if (!isEdit) return
  Object.assign(form.value,
    await api.get(`drivers/${route.params.id}/`).then(r=>r.data))
}
async function save(){
  try{
    if(isEdit)
      await api.put(`drivers/${route.params.id}/`, form.value)
    else
      await api.post('drivers/', form.value)
    router.push('/drivers')                // 適宜
  }catch(e){ alert(e.response?.data?.detail || '保存失敗') }
}
onMounted(async()=>{ await fetchMasters(); await fetchDriver() })
</script>

<template>
<div class="container-fluid py-4" style="max-width:640px">
  <h1 class="h4 mb-3">{{ isEdit ? 'ドライバー編集':'ドライバー登録' }}</h1>

  <div class="mb-3">
    <label class="form-label">ユーザー</label>
    <input v-model="form.user_name" class="form-control" :disabled="isEdit">
  </div>

  <div class="mb-3">
    <label class="form-label">店舗</label>
    <select v-model="form.store" class="form-select">
      <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
    </select>
  </div>

  <div class="row mb-3">
    <div class="col-md-4">
      <label class="form-label">電話番号</label>
      <input v-model="form.phone" class="form-control">
    </div>
    <div class="col-md-4">
      <label class="form-label">車種</label>
      <input v-model="form.car_type" class="form-control">
    </div>
    <div class="col-md-4">
      <label class="form-label">ナンバー</label>
      <input v-model="form.number" class="form-control">
    </div>
  </div>

  <div class="mb-3">
    <label class="form-label">メモ</label>
    <textarea v-model="form.memo" rows="3" class="form-control"></textarea>
  </div>

  <!-- NG キャスト -->
  <div class="mb-3 position-relative">
    <label class="form-label">NG キャスト</label>
    <input v-model="kw" @input="searchCast" class="form-control mb-1"
           placeholder="キャスト名検索で追加">
    <!-- 既存 -->
    <div class="mt-2" v-if="form.ng_casts.length">
      <span v-for="id in form.ng_casts" :key="id" class="badge bg-secondary me-2">
        {{ casts.find(c=>c.id===id)?.stage_name || id }}
        <button class="btn-close btn-close-white btn-sm ms-1"
                @click="removeNg(id)"></button>
      </span>
    </div>
    <!-- 検索候補 -->
    <ul v-if="showCand" class="list-group position-absolute w-100" style="z-index:5">
      <li v-for="c in cand" :key="c.id" class="list-group-item list-group-item-action"
          @click="addNg(c)">
        {{ c.stage_name }} / {{ c.store_name }}
      </li>
    </ul>
  </div>

  <button class="btn btn-primary" @click="save">保存</button>
</div>
</template>
