<!-- src/views/AdminCastForm.vue など --------------------------->
<script setup>
import { ref, onMounted, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import {
	api,
	getCastOptions, patchCastOption,
	searchCustomers, createCustomer,
	getShiftPlans,
} from '@/api'
import useZipcode from '@/utils/zipcode'

/* ---------- ルーティング ---------- */
const route	= useRoute()
const router = useRouter()
const isEdit = !!route.params.id					// id があれば「編集」

/* ---------- フォーム ---------- */
const form = ref({
	stage_name	: '',
	rank				: '',
	store			 : '',
	star_count	: 0,
	memo				: '',
	ng_customers: [],
	standby_places: [],
	price_mode	: 'DEFAULT',
})


 function ensureOneRow () {
	 if (form.value.standby_places.length === 0) {
		 form.value.standby_places.push(makeBlankPlace())
	 }
 }


function makeBlankPlace () {
	const p = reactive({
		zipcode	 : '',
		address	 : '',
		label		 : '',
		is_primary: false,
		zipErr		: '',
	})

	// 郵便番号 7 桁 → 住所自動補完
	const { zipcode, zipErr } = useZipcode({ value: '' }, { value: p })

	// composable と p を同期
	watch(zipcode, v => (p.zipcode = v))
	watch(() => p.zipcode, v => (zipcode.value = v))
	watch(zipErr,	e => (p.zipErr	= e))

	return p
}

/* 歩合 (%) —— null なら未設定 */
const commission_pct = ref(null)

/* ---------- マスター ---------- */
const options	 = ref([])
const ranks		 = ref([])
const stores		= ref([])
const customers = ref([])

/* ---------- キャスト固有 ---------- */
const castOpts = ref([])	 // option の ON / OFF
const shifts	 = ref([])	 // シフト一覧

/* ---------- NG 顧客検索 ---------- */
const kwNg	 = ref('')
const candNg = ref([])
const showCand = ref(false)

const findNg = async () => {
	if (kwNg.value.length < 2) { showCand.value = false; return }
	candNg.value	= await searchCustomers(kwNg.value)
	showCand.value = candNg.value.length > 0
}
function addNg (c) {
	if (!form.value.ng_customers.includes(c.id))
		form.value.ng_customers.push(c.id)
	kwNg.value = ''; showCand.value = false
}
function removeNg (id) {
	form.value.ng_customers =
		form.value.ng_customers.filter(x => x !== id)
}
async function addNgNew () {
	const name	= prompt('顧客名');	 if (!name)	return
	const phone = prompt('電話番号'); if (!phone) return
	const newC	= await createCustomer({ name, phone })
	addNg(newC)
}



/* ---------- データ取得 ---------- */
async function fetchMasters () {
	const [opt, rks, sts, cust] = await Promise.all([
		api.get('options/').then(r => r.data),
		api.get('ranks/').then(r => r.data),
		api.get('stores/').then(r => r.data),
		api.get('customers/').then(r => r.data),
	])
	;[options.value, ranks.value, stores.value, customers.value] = [opt, rks, sts, cust]
}

async function loadRate () {
	if (!isEdit) return
	const latest = await api.get('cast-rates/', {
		params: {
			cast_profile: route.params.id,
			ordering		: '-effective_from',
			limit			 : 1,
		},
	}).then(r => r.data[0])
	commission_pct.value = latest?.commission_pct ?? null
}


/** ① 行追加・削除 */
function addPlace ()	 { form.value.standby_places.push(makeBlankPlace()) }
function removePlace(i){ form.value.standby_places.splice(i,1) }

async function fetchCast () {
	if (!isEdit) return

	Object.assign(
		form.value,
		await api.get(`cast-profiles/${route.params.id}/`).then(r => r.data),
	)

	// ★ 待機場所
	form.value.standby_places =
		form.value.standby_places.map(p => reactive({ ...p, zipErr:'', zipcode:'' }))

	ensureOneRow() 

	castOpts.value = await getCastOptions(route.params.id)
	shifts.value	 = await getShiftPlans({ cast_profile: route.params.id })
	await loadRate()
}

/* ---------- Option トグル ---------- */
async function toggleOpt (row) {
	row.is_enabled = !row.is_enabled
	await patchCastOption(row.id, { is_enabled: row.is_enabled })
}

/* ---------- 保存 ---------- */
async function save () {
	try {

		const payload = {
			...form.value,
		standby_places: form.value.standby_places.map(p => ({
			label		 : p.label,
			address	 : p.address,
			zipcode	 : p.zipcode,	 // ★忘れてた
			is_primary: p.is_primary,
		})),
		}
		/* 1) CastProfile 保存 */
		let castId
		if (isEdit) {
			await api.put(`cast-profiles/${route.params.id}/`, payload)
			castId = route.params.id
		} else {
			const { data } = await api.post('cast-profiles/', payload)
			castId = data.id
		}

		/* 2) 歩合 (%) を upsert	*/
		if (commission_pct.value !== null) {
			const today = dayjs().format('YYYY-MM-DD')

			// ── 既存を探す ─────────────────
			const latest = await api.get('cast-rates/', {
				params: { cast_profile: castId,
									effective_from: today,				// ちょうど今日付
									limit: 1 }
			}).then(r => r.data[0])

			if (latest) {
				// 既に「今日付」の行がある → PATCH
				await api.patch(`cast-rates/${latest.id}/`, {
					commission_pct: commission_pct.value
				})
			} else {
				// 無ければ INSERT
				await api.post('cast-rates/', {
					cast_profile	: castId,
					commission_pct: commission_pct.value,
					effective_from: today
				})
			}
		}

		router.push('/casts')
	} catch (e) {
		alert(e.response?.data?.detail || '保存失敗')
	}
}

/* ---------- 初期化 ---------- */
onMounted(async () => {
	await fetchMasters()
	await fetchCast()
	ensureOneRow()

})
</script>


<template>
  <div
    class="container-fluid py-4"
    style="max-width:640px"
  >
    <h1 class="h4 mb-3">
      {{ isEdit ? 'キャスト編集' : 'キャスト登録' }}
    </h1>

    <div class="mb-3">
      <input
        v-model="form.stage_name"
        class="form-control"
        placeholder="源氏名"
      >
    </div>
    <section class="casts-area" />

    <div class="row mb-3">
      <div class="col-md-6">
        <label class="form-label">Rank</label>
        <select
          v-model="form.rank"
          class="form-select"
        >
          <option
            v-for="r in ranks"
            :key="r.id"
            :value="r.id"
          >
            {{ r.name }}
          </option>
        </select>
      </div>
      <div class="col-md-6">
        <label class="form-label">店舗</label>
        <select
          v-model="form.store"
          class="form-select"
        >
          <option
            v-for="s in stores"
            :key="s.id"
            :value="s.id"
          >
            {{ s.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- 歩合 (%) 入力 -->
    <div class="mb-3 col-md-4">
      <label class="form-label">歩合 (%)</label>
      <input
        v-model.number="commission_pct"
        type="number"
        class="form-control"
        min="0"
        max="100"
      >
    </div>


    <!-- ◆ 待機場所 ◆ -->
    <div class="mb-4">
      <label class="form-label">待機場所</label>

      <!-- 行 -->
      <div
        v-for="(p,i) in form.standby_places"
        :key="i"
        class="border p-3 mb-2 rounded"
      >
        <div class="row g-2 align-items-end">
          <!-- 郵便番号 -->
          <div class="col-md-3">
            <label class="form-label small">郵便番号</label>
            <input
              v-model="p.zipcode"
              class="form-control"
              placeholder="1500041"
            >
            <small class="text-danger">{{ p.zipErr }}</small>
          </div>

          <!-- 住所 -->
          <div class="col-md-6">
            <label class="form-label small">住所</label>
            <input
              v-model="p.address"
              class="form-control"
            >
          </div>

          <!-- ラベル -->
          <div class="col-md-2">
            <label class="form-label small">ラベル</label>
            <input
              v-model="p.label"
              class="form-control"
              placeholder="自宅 / 事務所 など"
            >
          </div>

          <!-- 既定 -->
          <div class="col-md-1 form-check">
            <input
              v-model="p.is_primary"
              type="radio"
              class="form-check-input"
              :value="true"
              @change="form.standby_places.forEach((r,j)=>{ if(j!==i) r.is_primary=false })"
            >
            <label class="form-check-label small">既定</label>
          </div>
        </div>

        <!-- 削除ボタン -->
        <button
          v-if="form.standby_places.length>1"
          class="btn btn-sm btn-outline-danger mt-2"
          @click="removePlace(i)"
        >
          削除
        </button>
      </div>

      <!-- 追加 -->
      <button
        class="btn btn-sm btn-outline-primary"
        @click="addPlace"
      >
        ＋ 追加
      </button>
    </div>


    <div class="mb-3">
      <label class="form-label">メモ</label>
      <textarea
        v-model="form.memo"
        rows="3"
        class="form-control"
      />
    </div>

    <!-- NG 顧客 -->
    <div class="mb-3 position-relative">
      <label class="form-label">NG 顧客</label>

      <!-- 検索入力 -->
      <input
        v-model="kwNg"
        class="form-control mb-1"
        placeholder="名前 or 電話で検索して追加"
        @input="findNg"
      >

      <!-- 候補リスト -->
      <div
        v-if="form.ng_customers.length"
        class="mt-2"
      >
        <span
          v-for="id in form.ng_customers"
          :key="id"
          class="badge bg-secondary me-2"
        >
          {{ customers.find(c => c.id === id)?.name || id }}
          <button
            class="btn-close btn-close-white btn-sm ms-1"
            @click="removeNg(id)"
          />
        </span>
      </div>

      <!-- multi-select は残しても OK（編集用） -->
      <select
        v-model="form.ng_customers"
        multiple
        class="form-select mt-2"
      >
        <option
          v-for="c in customers"
          :key="c.id"
          :value="c.id"
        >
          {{ c.name }} / {{ c.phone }}
        </option>
      </select>
    </div>

    <!-- Option NG (チェック＝利用可) -->
    <div class="mb-3">
      <label class="form-label">オプション（NG はチェックを外す）</label>

      <!-- 編集時: castOpts を表示 / 新規時: master options -->
      <div
        v-if="isEdit && castOpts.length"
        class="list-group"
      >
        <label
          v-for="co in castOpts"
          :key="co.id"
          class="list-group-item d-flex align-items-center gap-2"
        >
          <input
            type="checkbox"
            class="form-check-input mt-0"
            :checked="co.is_enabled"
            @change="toggleOpt(co)"
          >
          <span>{{ co.option_name }}</span>
        </label>
      </div>

      <!-- 新規登録フォームではマスタを全部 ON 状態で参考表示 -->
      <div
        v-else
        class="list-group"
      >
        <label
          v-for="o in options"
          :key="o.id"
          class="list-group-item d-flex align-items-center gap-2"
        >
          <input
            type="checkbox"
            class="form-check-input mt-0"
            checked
            disabled
          >
          <span>{{ o.name }}</span>
        </label>
      </div>
    </div>

    <div
      v-if="isEdit"
      class="mb-4"
    >
      <h5>登録シフト</h5>
      <table class="table table-sm">
        <thead class="table-light">
          <tr><th>日付</th><th>開始</th><th>終了</th><th>状態</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="s in shifts"
            :key="s.id"
          >
            <td>{{ s.date }}</td>
            <td>{{ s.start_at }}</td>
            <td>{{ s.end_at }}</td>
            <td>
              <span
                v-if="s.is_checked_in"
                class="badge bg-success"
              >IN</span>
              <span
                v-else
                class="badge bg-secondary"
              >予定</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <button
      type="button"
      class="btn btn-primary"
      @click="save"
    >
      保存
    </button>
  </div>
</template>
