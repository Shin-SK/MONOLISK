<!-- BillModal.vue -->
<script setup>
/* ── 必要最小限のインポート ───────────────────── */
import { reactive, ref, watch, computed, onMounted } from 'vue'
import BaseModal      from '@/components/BaseModal.vue'
import Avatar      from '@/components/Avatar.vue'
import { api, updateBillCasts, fetchCasts, fetchMasters, fetchTables, addBillItem, deleteBillItem, closeBill } from '@/api'
import dayjs from 'dayjs'

/* ── props / emit ─────────────────────────────── */
const props = defineProps({
  modelValue  : Boolean,
  bill        : Object,
  serviceRate : { type: Number, default: 0.3 },
  taxRate     : { type: Number, default: 0.1 },
})
const emit  = defineEmits(['update:modelValue','saved'])

/* ── v‑model（開閉） ─────────────────────────── */
const visible = computed({
  get : () => props.modelValue,
  set : v  => emit('update:modelValue', v)
})

/* ── キャスト一覧を API からロード ─────────────── */
const casts = ref([])               // [{id, stage_name, …}]
const masters = ref([])
const tables   = ref([])
const castKeyword = ref('')

onMounted(async () => {
  try {
    const storeId = props.bill?.table?.store ?? ''   // ← 無ければ全店
    casts.value   = await fetchCasts(storeId)
	  masters.value   = await fetchMasters(storeId)
    tables.value  = await fetchTables(storeId)
  } catch (e) {
    console.error('casts fetch failed', e)
  }
})

/* ---------- state ---------- */
const mainCastIds  = ref([])
const freeCastIds  = ref([])
const inhouseSet   = ref(new Set())



function toggleInhouse(cid) {
  const s = inhouseSet.value
  if (s.has(cid)) {
    s.delete(cid)
  } else {
    s.add(cid)
    // free に居なければ追加しておく
    if (!freeCastIds.value.includes(cid))
      freeCastIds.value.push(cid)
  }
}


/* ---------- オーダー ---------- */

const CAT_PRESET = [
  { value: 'drink',        label: 'ドリンク'   },
  { value: 'extension',    label: '延長'       },
  { value: 'extensionVip', label: 'VIP延長'    },
]

const catOptions = computed(() =>
  CAT_PRESET.filter(p =>
    masters.value.some(m => m.category === p.value)
  )
)
const selectedCat  = ref('drink')   // デフォルトは drink

const orderMasters = computed(() =>
  masters.value.filter(m => m.category === selectedCat.value)
)


/* --- 会計確定処理 --- */
const settleAmount = ref(null)

async function settleBill () {
	if (!settleAmount.value || settleAmount.value <= 0) return
	try{
		/*  バックエンド側で settled_total と closed_at を確定させる */
		await closeBill(props.bill.id, { settled_total: settleAmount.value })
		emit('saved', props.bill.id)       // 親に再フェッチさせる
	}catch(e){
		console.error('settle failed', e)
		alert('会計に失敗しました')
	}
}

/* ------- draft ------- */
const draftCode = ref('')   // 'set60' など
const pax       = ref(1)    // 人数
const draftMasterId = ref(null)   // 品名
const draftCastId   = ref(null)   // 誰が注文したか（任意）
const draftQty      = ref(1)      // 数量

/* ── 編集フォーム（卓番号 & nominated_casts だけ） ─ */
const form = reactive({
  table_id        : null,
  nominated_casts : [],
  inhouse_casts   : []  
})


async function cancelItem(idx, item){
  if(!confirm('この注文をキャンセルしますか？')) return

  try{
    await deleteBillItem(props.bill.id, item.id)   // ← billId も渡す
    props.bill.items.splice(idx, 1)                // UI から即時削除
  }catch(e){
    console.error('cancel failed', e)
    alert('キャンセルに失敗しました')
  }
}

/* ------- コースとか ------- */

const COURSE_CATS = ['setMale','setVip','setFemale']

const courseOptions = computed(() =>
  COURSE_CATS.map(cat => {
    const m = masters.value.find(v => v.category === cat)
    return m ? {                    // UI で使う最低限
      id   : m.id,                  // ← addBillItem 用
      code : m.code,                // ← v-model 用
      label: m.name,                // ← ボタン表示
    } : null
  }).filter(Boolean)                // 未登録カテゴリは除外
)


/* ── コースを直通で伝票へ載せる ── */
async function chooseCourse(opt){           // opt = {id, code, label}
  try {
    // ① 伝票へ即 POST
    const newItem = await addBillItem(props.bill.id, {
      item_master : opt.id,
      qty         : pax.value           // ← 人数をそのまま使う
    })
    // ② フロント側に即反映
    props.bill.items.push(newItem)

    // ③ テーブルが変更されていれば PATCH で確定
    if (form.table_id !== props.bill.table?.id) {
      await api.patch(`billing/bills/${props.bill.id}/`, {
        table_id: form.table_id
      })
    }

  } catch(e){
    console.error('add course failed', e)
    alert('コース追加に失敗しました')
  }
}


/* ------- コース追加ボタン専用 ------- */
function addCourse () {
  if (!draftCode.value){
    alert('セットを選択');
    return;
  }
  chooseCourse(draftCode.value);   // ← 既存ヘルパを再利用
}


/* ------- 注文とか ------- */
function addSingle () {
  if (!draftMasterId.value) { alert('品名を選択'); return }
  if (draftQty.value <= 0)  { alert('数量を入力'); return }

  pending.value.push({
    master_id : draftMasterId.value,
    qty       : draftQty.value,
    cast_id   : draftCastId.value || null
  })

  // リセット
  draftMasterId.value = null
  draftCastId.value   = null
  draftQty.value      = 1
}



const currentCasts = computed(() => {
  // mainCastIds だけ先に並べる
  const list = mainCastIds.value
    .map(id => casts.value.find(c => c.id === id))
    .filter(Boolean)
    .map(c => ({ ...c, role:'main' }))

  const others = new Set([
    ...freeCastIds.value,
    ...inhouseSet.value          // ← ここを足す！
  ])

  others.forEach(id => {
    // main と重複しないように
    if (!mainCastIds.value.includes(id)) {
      const c = casts.value.find(c => c.id === id)
      if (c) {
        list.push({
          ...c,
          role    : 'free',             // 見た目は free 行
          inhouse : inhouseSet.value.has(id)
        })
      }
    }
  })

  return list
})



/* ------- キャスト絞り込み ------- */
const filteredCasts = computed(() => {
  if (!castKeyword.value.trim()) return casts.value          // 空なら全件
  const kw = castKeyword.value.toLowerCase()
  return casts.value.filter(c => c.stage_name.toLowerCase().includes(kw))
})


/* ---------- 本指名に変わるやつ ---------- */
function toggleMain(id){
  if (mainCastIds.value.includes(id)){
    // 解除
    mainCastIds.value = mainCastIds.value.filter(x => x !== id)
  }else{
    mainCastIds.value.push(id)
    // free 側に無ければ追加（want both? ⇒今のロジックで除去されても OK）
    if (!freeCastIds.value.includes(id))
      freeCastIds.value.push(id)
  }
}

/* ---------- ヘッダーに入れる基礎情報 ---------- */
const headerInfo = computed(() => {
  const b = props.bill
  if (!b) return {}

  const fmt = (dt) => dt ? dayjs(dt).format('HH:mm') : '‑'

  return {
    id     : b.id,
    table  : b.table?.number ?? '‑',
    start  : fmt(b.opened_at),
    end    : fmt(b.expected_out),
    sets   : b.set_rounds ?? 0,
    extCnt : b.ext_minutes ? Math.ceil(b.ext_minutes / 30) : 0,
  }
})


/* ------- 現状（確定済み）計算 ------------------- */
const current = computed(() => {
  const sub = props.bill.items.reduce(
    (s, it) => s + it.qty *
      (masters.value.find(m => m.id === it.item_master)?.price_regular || it.price || 0),
    0
  )
  const svc = Math.round(sub * props.serviceRate)
  const tax = Math.round((sub + svc) * props.taxRate)
  return { sub, svc, tax, total: sub + svc + tax }
})

/* ------- draft を pending に載せる ---------- */
const pending = ref([])   // [{ master_id, qty }]


/* ------- 仮計算 本計算はバックエンドで ---------- */

const preview = computed(() => {
  const sub = pending.value.reduce(
    (s, i) =>
      s + i.qty * (masters.value.find(m => m.id === i.master_id)?.price_regular || 0),
    0
  )
  const svc = Math.round(sub * props.serviceRate)  // ← 追加した prop を参照
  const tax = Math.round((sub + svc) * props.taxRate)
  return { sub, svc, tax, total: sub + svc + tax }
})

/* ---------- 伝票読み込み時 ---------- */
watch(() => props.bill, b => {
  if (!b) return

const stayNom = b.stays?.filter(s => s.stay_type==='nom').map(s=>s.cast.id) ?? []
const stayFree = b.stays?.filter(s => s.stay_type==='free').map(s=>s.cast.id) ?? []
const stayIn   = b.stays?.filter(s => s.stay_type==='in').map(s=>s.cast.id)   ?? []

mainCastIds.value  = stayNom
freeCastIds.value  = [...new Set([...stayFree, ...stayIn])]
inhouseSet.value   = new Set(stayIn)

form.table_id = b.table?.id ?? null
}, { immediate:true })

/* ---------- ウォッチャー ---------- */
/* main が変わったら free から除去 */
watch(mainCastIds, list => {
  const filtered = freeCastIds.value.filter(id => !list.includes(id))
  if (filtered.length !== freeCastIds.value.length) {
    freeCastIds.value = filtered
  }
})

watch(freeCastIds, list => {
 const deduped = list.filter(id => !mainCastIds.value.includes(id))
  if (deduped.length !== list.length) {
    freeCastIds.value = deduped      // 変化がある時だけ再代入
    return                           // ここで終われば再トリガは 1 回で済む
  }
})


/* キャストをリストから外すだけの共通関数（JSのみ） */
function removeCast(id) {
  // 本指名だったら解除
  mainCastIds.value = mainCastIds.value.filter(c => c !== id)
  // フリー配列から除外
  freeCastIds.value = freeCastIds.value.filter(c => c !== id)

  // 場内セットからも除外
  inhouseSet.value.delete(id)
}

/* ── 保存ボタン ─────────────────────────────── */
async function save () {

  for (const it of pending.value) {
    try {
    const payload = {
      item_master : it.master_id,
      qty         : it.qty,
    }
    if (it.cast_id != null) payload.served_by_cast_id = it.cast_id

    const newItem = await addBillItem(props.bill.id, payload)
      props.bill.items.push(newItem)
      
    } catch (e) {
      console.error('add item failed', e)
    }
  }
  pending.value = []   // クリア（UI からも消す）

  /* ----------------------------------------------------
   * 2.  Bill 本体の更新（卓 / 指名 / 場内）
   * -------------------------------------------------- */
    try {
      await updateBillCasts(props.bill.id, {
        nomIds  : [...mainCastIds.value],
        inIds   : [...inhouseSet.value],
        freeIds : [...freeCastIds.value],
      })

      // 卓番号を変えたときだけ PATCH
      if (form.table_id !== props.bill.table?.id) {
        await api.patch(`billing/bills/${props.bill.id}/`, { table_id: form.table_id })
      }
    } catch (e) {
      console.error('updateBillCasts failed', e)
    }
  /* ----------------------------------------------------
   * 3.  親コンポーネントへ通知してモーダル閉じ
   * -------------------------------------------------- */
  emit('saved', props.bill.id)
}

</script>

<template>
  <!-- 伝票がまだ無い瞬間は描画しない -->
  <BaseModal v-if="props.bill" v-model="visible">
  <template #header>
    <div class="modal-header align-items-center justify-content-end gap-3">
      <div class="d-flex flex-wrap gap-3">
        <span class="fs-3 fw-bold">
          {{ headerInfo.sets }}SET 
        </span>

        <span class="fs-3 fw-bold">
          {{ headerInfo.start }} 〜 {{ headerInfo.end }}
        </span>

        <span v-if="headerInfo.extCnt">
          延長 <b>{{ headerInfo.extCnt }}</b> 回
        </span>
      </div>

      <button class="btn-close" @click="visible = false" style="margin-left: unset;"></button>
    </div>
  </template>

    <div class="position-relative p-4 d-grid gap-4 h-100" style="grid-template-columns:auto 1fr 1fr;">
        <div class="outer d-flex flex-column gap-4">
          <!-- 伝票番号 -->
          <div class="d-flex flex-column align-items-center gap-2">
            <span class="badge bg-primary text-light">伝票番号</span>
            <span>{{ props.bill.id }}</span>
          </div>
          <!-- テーブル番号 -->
          <div class="wrap d-flex flex-column align-items-center gap-2">
            <div class="badge bg-primary text-light">テーブル</div>
            <select class="form-select text-end"
                    style="width: 80px;"
                    v-model.number="form.table_id">
              <option class="text-center" :value="null"> - </option>
              <option class="text-center" v-for="t in tables" :key="t.id" :value="t.id">
                {{ t.number }}
              </option>
            </select>
          </div>
          <!-- 人数 -->
          <div class="wrap d-flex flex-column align-items-center gap-2">
            <div class="badge bg-primary text-light">人数</div>
            <select class="form-select text-center" style="width: 80px;"
                    v-model.number="pax">
              <option v-for="n in 12" :key="n" :value="n">{{ n }}</option>
            </select>
          </div>

          <!-- コース -->
          <div class="wrap d-flex flex-column align-items-center gap-2">
            <div class="badge bg-primary text-light">セット</div>
            <div class="d-flex flex-column gap-2">
              <button
                v-for="c in courseOptions"
                :key="c.code"
                class="btn btn-outline-dark d-flex justify-content-center"
                @click="chooseCourse(c)"
              >
                {{ c.label }}
              </button>
            </div>
          </div>
        </div>
      <div class="outer d-flex flex-column gap-4">
      <!-- 現在ついているキャストエリア ------------------------------- -->
      <div class="mb-3">

        <!-- (D) 誰もいない時 -->
        <div v-if="!currentCasts.length"
            class="border border‑2 rounded p‑4 text-center text-muted d-flex justify-content-center align-items-center bg-light" style="min-height: 100px;">
          キャストを選択してください
        </div>

        <!-- (A,B,C) 一覧 -->
        <div v-else class="d-flex flex-wrap gap-2 bg-light px-3 py-5 rounded">
          <template v-for="c in currentCasts" :key="c.id">
            <!-- 本指名 -->
            <div v-if="c.role==='main'"
                  class="btn rounded border-secondary bg-white py-3 px-3 d-flex align-items-center fw-bold"
                  role="button">
              <!-- ✕ボタン：単なるアイコンに click を付与 -->
              <i class="bi bi-x me-2"
                  role="button"
                  @click.stop="removeCast(c.id)"></i>
              <Avatar :url="c.avatar_url" :alt="c.stage_name" size="28" class="me-1" />
              <span>{{ c.stage_name }}</span>
              <span class="badge bg-danger text-white ms-1 d-flex align-items-center">
                本指名
              </span>
            </div>

            <!-- フリー -->
            <div v-else
                  class="btn rounded border-secondary fw-bold bg-white py-3 px-3 d-flex align-items-center gap-1"
                  role="button"
                  @click="toggleInhouse(c.id)">
              <!-- ✕アイコン -->
              <i class="bi bi-x me-2"
                  role="button"
                  @click.stop="removeCast(c.id)"></i>
              <Avatar :url="c.avatar_url" :alt="c.stage_name" size="28" class="me-1" />
              <span>{{ c.stage_name }}</span>
              <span class="badge"
                    :class="c.inhouse ? 'bg-success' : 'bg-secondary'">
                {{ c.inhouse ? '場内' : 'フリー' }}
              </span>
            </div>
          </template>
        </div>
      </div>


      <!-- ▼キャスト選択　一括表示 -->
      <div class="mb-3 cast-select">
        <div class="input-group mb-4">
          <span class="input-group-text"><i class="bi bi-search"></i></span>
          <input  type="text"
                  class="form-control"
                  placeholder="キャスト名で絞り込み"
                  v-model="castKeyword">
          <!-- クリアボタン（×）-->
          <button class="d-flex align-items-center p-2"
                  v-if="castKeyword"
                  @click="castKeyword=''">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
        <div class="d-flex flex-wrap gap-2">
          <template v-for="c in filteredCasts" :key="c.id">
            <!-- free 用チェックボックス -->
            <input  class="btn-check"
                    type="checkbox"
                    :id="`cast-${c.id}`"
                    :value="c.id"
                    v-model="freeCastIds">
            <label  class="btn d-flex align-items-center"
                    :class=" (freeCastIds.includes(c.id) || mainCastIds.includes(c.id))
                            ? 'bg-secondary-subtle'
                            : 'bg-light'"
                    :for="`cast-${c.id}`">
              <!-- Avatar(共通コンポーネント) -->
              <Avatar :url="c.avatar_url" :alt="c.stage_name" size="28" class="me-1"/>
              {{ c.stage_name }}
              <!-- 本指名バッジ -->
              <span class="badge ms-2"
                    :class="mainCastIds.includes(c.id) ? 'bg-danger' : 'bg-secondary'"
                    @click.stop="toggleMain(c.id)">
                本指名
              </span>
            </label>
          </template>
        </div>
      </div>

        
      <button class="btn btn-primary w-100 mt-auto" @click="save">保存</button>
    </div>
    <div class="outer">

      <!-- ── 単品注文フォーム ───────────────────────── -->
      <div class="mb-3 border-top pt-3">
        <label class="form-label fw-bold">単品注文</label>

        <div class="d-grid align-items-stretch gap-2 mb-2"
            style="grid-template-columns: 2fr 3fr 3fr 1fr auto;">

          <!-- 2 カテゴリ -->
          <select class="form-select" v-model="selectedCat">
            <option v-for="o in catOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>

          <!-- 1 注文キャスト -->
          <select class="form-select" v-model="draftCastId">
            <option :value="null">‑ CAST ‑</option>
            <option v-for="c in casts" :key="c.id" :value="c.id">{{ c.stage_name }}</option>
          </select>

          <!-- 3 品名（選択したカテゴリだけが出る） -->
          <select class="form-select" v-model="draftMasterId">
            <option :value="null">‑ ITEM ‑</option>
            <option v-for="m in orderMasters" :key="m.id" :value="m.id">{{ m.name }}</option>
          </select>

          <!-- 4 -->
            <select class="form-select text-center"
                    v-model.number="draftQty">
              <option v-for="n in 12" :key="n" :value="n">{{ n }}</option>
            </select>
          <!-- <input type="number" min="1"
                class="form-control text-end"
                v-model.number="draftQty"> -->

          <!-- 5 追加ボタン -->
          <button class="btn btn-dark text-light" @click="addSingle">
            <i class="bi bi-cart-plus-fill"></i>
          </button>
        </div>
      </div>
      <!-- 🛒 ここが「仮確定」カート ----------------------------- -->
      <ul v-if="pending.length" class="list-group mb-3">
        <li v-for="(it,i) in pending" :key="i"
            class="list-group-item d-flex justify-content-between align-items-center">

          <span>
            <!--  masters で検索に変更 -->
            {{ masters.find(m => m.id === it.master_id)?.name }}
            <small class="text-muted ms-2">
              {{ casts.find(c => c.id === it.cast_id)?.stage_name || '‑' }}
            </small>
          </span>

          <span class="d-flex align-items-center gap-2">
            <span class="badge bg-secondary">{{ it.qty }}</span>
            <i class="bi bi-trash text-danger" role="button"
              @click="pending.splice(i,1)"></i>
          </span>
        </li>
      </ul>

<!-- ▼pending がある時だけ：追加後の仮計算 ------- -->
<table v-if="pending.length"
       class="table table-sm mb-3 text-end border-top">
  <tbody>
    <tr><th class="text-start">小計(仮)</th>      <td>{{ preview.sub.toLocaleString() }}</td></tr>
    <tr><th class="text-start">サービス料(仮)</th><td>{{ preview.svc.toLocaleString() }}</td></tr>
    <tr><th class="text-start">消費税(仮)</th>    <td>{{ preview.tax.toLocaleString() }}</td></tr>
    <tr class="fw-bold">
      <th class="text-start">合計(仮)</th>
      <td>{{ preview.total.toLocaleString() }}</td>
    </tr>
  </tbody>
</table>

      <div class="d-flex my-5">
        <button class="btn btn-warning flex-fill" @click="save">注文</button>
      </div>


      <table class="table table-sm table-striped">
        <thead>
          <tr><th></th><th>品名</th><th>キャスト</th><th class="text-end">Qty</th><th class="text-end">小計</th></tr>
        </thead>
        <tbody>
          <tr v-for="(it, idx) in props.bill.items" :key="it.id">
            <!-- キャンセル -->
            <td class="text-center">
              <i class="bi bi-x text-danger" role="button"
               @click="cancelItem(idx, it)"></i>
            </td>
            <td>{{ it.name }}</td>
            <td>{{ it.served_by_cast?.stage_name || '‑' }}</td>
            <td class="text-end">{{ it.qty }}</td>
            <td class="text-end">{{ it.subtotal.toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>

<!-- ▼いつも出す：現状確定分 -------------------- -->
<table class="table table-sm mb-3 text-end">
  <tbody>
    <tr><th class="text-start">小計</th>      <td>{{ current.sub.toLocaleString() }}</td></tr>
    <tr><th class="text-start">サービス料</th><td>{{ current.svc.toLocaleString() }}</td></tr>
    <tr><th class="text-start">消費税</th>    <td>{{ current.tax.toLocaleString() }}</td></tr>
    <tr class="fw-bold">
      <th class="text-start">合計</th>
      <td>{{ current.total.toLocaleString() }}</td>
    </tr>
  </tbody>
</table>

<div class="d-flex align-items-center gap-2 mt-4">
	<label class="fw-bold mb-0">会計金額</label>
	<input type="number"
		   class="form-control text-end"
		   style="max-width:120px;"
		   v-model.number="settleAmount">
	<button class="btn btn-info"
			:disabled="!settleAmount"
			@click="settleBill">
		会計
	</button>
</div>


    </div>

    </div>



  </BaseModal>
</template>



<style>

.btn-check:checked + .btn, :not(.btn-check) + .btn:active, .btn:first-child:active, .btn.active, .btn.show
{
  border: unset !important;
}

</style>