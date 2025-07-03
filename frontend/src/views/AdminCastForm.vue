<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, getCastOptions, patchCastOption } from '@/api'
import { searchCustomers, createCustomer } from '@/api'   // ★ 追加
import { getShiftPlans } from '@/api'

const route   = useRoute()
const router  = useRouter()
const isEdit  = !!route.params.id

const form = ref({
  stage_name:'', rank:'', store:'', star_count:0,
  memo:'', ng_customers:[], price_mode:'DEFAULT'
})
const options   = ref([])
const castOpts = ref([])
const ranks     = ref([])
const stores    = ref([])
const customers = ref([])
const shifts = ref([]) 


/* ---------- NG顧客検索用 ---------- */
const kwNg     = ref('')
const candNg   = ref([])
const showCand = ref(false)

const findNg = async () => {
  if (kwNg.value.length < 2) { showCand.value = false; return }
  candNg.value = await searchCustomers(kwNg.value)
  showCand.value = candNg.value.length > 0
}

function addNg(c) {
  if (!form.value.ng_customers.includes(c.id))
    form.value.ng_customers.push(c.id)
  kwNg.value = ''
  showCand.value = false
}

function removeNg(id) {                     // ★ 追加
  form.value.ng_customers =
    form.value.ng_customers.filter(x => x !== id)
}

async function addNgNew() {
  const name  = prompt('顧客名');        if (!name)  return
  const phone = prompt('電話番号');      if (!phone) return
  const newC  = await createCustomer({ name, phone })
  addNg(newC)
}


/* 取得 */
async function fetchMasters() {
  const [opt, rks, sts, cust] = await Promise.all([
    api.get('options/').then(r=>r.data),
    api.get('ranks/').then(r=>r.data),
    api.get('stores/').then(r=>r.data),
    api.get('customers/').then(r=>r.data)
  ])
  ;[options.value, ranks.value, stores.value, customers.value] = [opt, rks, sts, cust]
}

async function fetchCast() {
  if (!isEdit) return
  Object.assign(form.value,
    await api.get(`cast-profiles/${route.params.id}/`).then(r=>r.data))

	castOpts.value = await getCastOptions(route.params.id)
  /* そのキャストの全シフト */
  shifts.value = await getShiftPlans({ cast_profile: route.params.id })
}


/* Option の ON/OFF を即保存 */
async function toggleOpt(row) {
  row.is_enabled = !row.is_enabled
  await patchCastOption(row.id, { is_enabled: row.is_enabled })
}

/* 保存 */
async function save() {
  try {
    if (isEdit)
      await api.put(`cast-profiles/${route.params.id}/`, form.value)
    else
      await api.post('cast-profiles/', form.value)
    router.push('/casts')
  } catch(e) {
    alert(e.response?.data?.detail || '保存失敗')
  }
}

onMounted(async () => {
  await fetchMasters()
  await fetchCast()
})
</script>

<template>
<div class="container-fluid py-4" style="max-width:640px">
	
  <h1 class="h4 mb-3">{{ isEdit ? 'キャスト編集' : 'キャスト登録' }}</h1>

  <div class="mb-3">
    <label class="form-label">源氏名</label>
    <input v-model="form.stage_name" class="form-control" />
  </div>

  <div class="row mb-3">
    <div class="col-md-6">
      <label class="form-label">Rank</label>
      <select v-model="form.rank" class="form-select">
        <option v-for="r in ranks" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
    </div>
    <div class="col-md-6">
      <label class="form-label">店舗</label>
      <select v-model="form.store" class="form-select">
        <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>
  </div>

  <div class="mb-3">
    <label class="form-label">メモ</label>
    <textarea v-model="form.memo" rows="3" class="form-control"></textarea>
  </div>

	<!-- NG 顧客 -->
	<div class="mb-3 position-relative">
		<label class="form-label">NG 顧客</label>

		<!-- 検索入力 -->
		<input v-model="kwNg" @input="findNg" class="form-control mb-1"
				placeholder="名前 or 電話で検索して追加">

		<!-- 候補リスト -->
		<div class="mt-2" v-if="form.ng_customers.length">
			<span v-for="id in form.ng_customers" :key="id" class="badge bg-secondary me-2">
				{{ customers.find(c => c.id === id)?.name || id }}
				<button class="btn-close btn-close-white btn-sm ms-1"
						@click="removeNg(id)"></button>
			</span>
		</div>

		<!-- multi-select は残しても OK（編集用） -->
		<select multiple class="form-select mt-2" v-model="form.ng_customers">
			<option v-for="c in customers" :key="c.id" :value="c.id">
				{{ c.name }} / {{ c.phone }}
			</option>
		</select>
	</div>

	<!-- Option NG (チェック＝利用可) -->
	<div class="mb-3">
	<label class="form-label">オプション（NG はチェックを外す）</label>

	<!-- 編集時: castOpts を表示 / 新規時: master options -->
	<div class="list-group" v-if="isEdit && castOpts.length">
		<label v-for="co in castOpts" :key="co.id"
			class="list-group-item d-flex align-items-center gap-2">
		<input type="checkbox" class="form-check-input mt-0"
				:checked="co.is_enabled"
				@change="toggleOpt(co)" />
		<span>{{ co.option_name }}</span>
		</label>
	</div>

	<!-- 新規登録フォームではマスタを全部 ON 状態で参考表示 -->
	<div class="list-group" v-else>
		<label v-for="o in options" :key="o.id"
			class="list-group-item d-flex align-items-center gap-2">
		<input type="checkbox" class="form-check-input mt-0" checked disabled />
		<span>{{ o.name }}</span>
		</label>
	</div>
	</div>

  <div class="mb-4" v-if="isEdit">
    <h5>登録シフト</h5>
    <table class="table table-sm">
      <thead class="table-light"><tr><th>日付</th><th>開始</th><th>終了</th><th>状態</th></tr></thead>
      <tbody>
        <tr v-for="s in shifts" :key="s.id">
          <td>{{ s.date }}</td>
          <td>{{ s.start_at }}</td>
          <td>{{ s.end_at }}</td>
          <td>
            <span v-if="s.is_checked_in" class="badge bg-success">IN</span>
            <span v-else class="badge bg-secondary">予定</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="btn btn-secondary disabled">
    保存
  </div>

</div>
</template>
