<script setup>
/* ── 必要最小限のインポート ───────────────────── */
import { reactive, ref, watch, computed, onMounted } from 'vue'
import BaseModal      from '@/components/BaseModal.vue'
import { updateBill, fetchCasts, fetchMasters, addBillItem, deleteBillItem, closeBill } from '@/api'

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

onMounted(async () => {
  try {
    const storeId = props.bill?.table?.store ?? ''   // ← 無ければ全店
    casts.value   = await fetchCasts(storeId)
	masters.value   = await fetchMasters(storeId)
  } catch (e) {
    console.error('casts fetch failed', e)
  }
})

/* ---------- state ---------- */
const mainCastIds  = ref([])
const freeCastIds  = ref([])
const inhouseSet   = ref(new Set())


/* コース用マップ（読み取り専用） */
const courseMap = computed(() => Object.fromEntries(
  courseOptions.value.map(o => [o.code, { id:o.id, label:o.label }])
))


function toggleInhouse(cid) {
  const s = inhouseSet.value
  s.has(cid) ? s.delete(cid) : s.add(cid)
}

const activeTab = ref('main')

const drinkMasters = computed(() =>
  masters.value.filter(m => m.category === 'drink')
)

const settleAmount = ref(null)

/* --- 会計確定処理 --- */
async function settleBill () {
	if (!settleAmount.value || settleAmount.value <= 0) return
	try{
		/* ★ バックエンド側で settled_total と closed_at を確定させる */
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
/* ボタン表示順とラベル */
const labelMap = { set60:'SET60', set60_vip:'VIP60', ext30:'延長30', ext30_vip:'VIP延30' }
const courseOrder = ['set60','set60_vip','ext30','ext30_vip']

const courseOptions = computed(() =>
  courseOrder.map(code => {
    const m = masters.value.find(v => v.code === code)
    return m ? { id:m.id, code, label:labelMap[code]||m.name } : null
  }).filter(Boolean)
)

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
  // mainCast が先頭、それ以外は freeCastIds の順
  const list = mainCastIds.value
    .map(id => {
      const mc = casts.value.find(c => c.id === id)
      return mc ? { ...mc, role: 'main' } : null
    })
    .filter(Boolean)
  freeCastIds.value.forEach(fid => {
    const fc = casts.value.find(c => c.id === fid)
    if (fc) {
      list.push({
        ...fc,
        role : 'free',
        inhouse: inhouseSet.value.has(fid)
      })
    }
  })
  return list
})

/* ── 追加：コースを即時 pending へ載せる ── */
function chooseCourse(code) {
  if (!code) return                           // safety
  const c = courseMap.value[code]             // { id, label }
  if (!c) { alert('コースを選択'); return }

  pending.value.push({                        // ★ 常に新行を追加
    master_id : c.id,
    qty       : pax.value,
    cast_id   : null                          // コースなのでキャスト不要
  })

  // UI リセット
  draftCode.value = ''
  pax.value       = 1
}


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

function addDraft () {
  const m = courseOptions.value.find(o => o.code === draftCode.value)
  if (!m)           { alert('コースを選択'); return }
  if (pax.value<=0) { alert('人数を入力');  return }

  pending.value.push({ master_id:m.id, qty:pax.value })
  draftCode.value = '';  pax.value = 1
}

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
/* ---- ① stays から状態を取り出す ---- */
const stayFree = b.stays
                  ?.filter(s => s.stay_type === 'free')
                  .map(s => s.cast.id) ?? []
const stayIn   = b.stays
                  ?.filter(s => s.stay_type === 'in')
                  .map(s => s.cast.id) ?? []

/* ---- ② 本指名は “nominated の先頭” を採用 ---- */
const nominated = b.nominated_casts ?? []
mainCastIds.value = nominated.length ? [nominated[0]] : []

/* ---- ③ フリー = 先頭以外の nominated ＋ stayFree − 本指名 ---- */
const tmpFree = [...nominated.slice(1), ...stayFree]
freeCastIds.value = Array.from(
  new Set(tmpFree.filter(id => !mainCastIds.value.includes(id)))
)

/* ---- ④ 場内セット ---- */
inhouseSet.value = new Set(stayIn)

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
  // ① main と重複を排除（必要なときだけ代入）
  const deduped = list.filter(id => !mainCastIds.value.includes(id))
  if (deduped.length !== list.length) {
    freeCastIds.value = deduped      // 変化がある時だけ再代入
    return                           // ここで終われば再トリガは 1 回で済む
  }
  // ② 場内セットを同期
  inhouseSet.value = new Set([...inhouseSet.value]
                              .filter(id => freeCastIds.value.includes(id)))
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

  /* ----------------------------------------------------
   * 1.  pending の注文を確定登録
   *     addBillItem が “最新 Bill 全体” を返す想定なので、
   *     返ってきたオブジェクトで props.bill を即時更新する
   * -------------------------------------------------- */
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

    const payload = {
      nominated_casts :
        mainCastIds.value.length               // 本指名が 1 人以上いるときだけ
       ? [...mainCastIds.value, ...freeCastIds.value]
       : [],  
      inhouse_casts_w : [...inhouseSet.value],
      table_id        : form.table_id
    }
      
  await updateBill(props.bill.id, payload)
  
  } catch (e) {
    console.error('update bill failed', e)
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
    <div class="position-relative p-4 d-grid gap-4 h-100" style="grid-template-columns: 1fr 1fr;">
      <div class="outer d-flex flex-column gap-4">
        <!-- 卓番号 -->
        <div class="d-flex gap-4">
          <div class="d-flex align-items-center gap-2">
            <span><i class="bi bi-journal fs-5"></i></span>
            <span>{{ props.bill.id }}</span>
          </div>
          <div class="wrap d-flex align-items-center">
            <div class="d-flex align-items-center me-2"><i class="bi bi-fork-knife fs-5"></i></div>
            <input type="number"
              class="form-control text-end"
              style="width: 62px;"
              v-model.number="form.table_id"
              >
          </div>
          <div class="d-flex gap-2 flex-wrap">
            <template v-for="c in courseOptions" :key="c.code">
            <input class="btn-check" type="radio" :id="`c-${c.code}`"
                :value="c.code" v-model="draftCode">
            <label class="btn d-flex align-items-center"
                :class="draftCode===c.code ? 'btn-dark':'btn-outline-dark'"
                :for="`c-${c.code}`">{{ c.label }}</label>
            </template>
          </div>

          <div class="d-flex align-items-center" style="max-width:160px;">
            <div class="me-2"><i class="bi bi-people-fill fs-3"></i></div>
            <input type="number" min="1" class="form-control text-end" style="width: 62px;" v-model.number="pax">
          </div>
        <button class="ms-auto"
                :disabled="!draftCode"
                @click="chooseCourse(draftCode)">
          <i class="bi bi-cart-plus-fill btn btn-dark text-light"></i>
        </button>

        </div>

      <!-- ★ 現在ついているキャストエリア ------------------------------- -->
      <div class="mb-3">

        <!-- (D) 誰もいない時 -->
        <div v-if="!currentCasts.length"
            class="border border‑2 rounded p‑4 text-center text-muted">
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
              <span>{{ c.stage_name }}</span>
              <span class="badge"
                    :class="c.inhouse ? 'bg-success' : 'bg-secondary'">
                {{ c.inhouse ? '場内' : 'フリー' }}
              </span>
            </div>
          </template>
        </div>
      </div>

        <!-- ★ 指名タブ -->
        <nav class="nav nav-tabs mb-3">
          <button class="nav-link"
                  :class="{ active: activeTab==='main' }"
                  @click="activeTab='main'">本指名</button>
          <button class="nav-link"
                  :class="{ active: activeTab==='free' }"
                  @click="activeTab='free'">フリー</button>
        </nav>

        <!-- ===================== 本指名タブ ===================== -->
        <div v-if="activeTab==='main'" class="mb-3">
          <div class="d-flex flex-wrap gap-2">
            <template v-for="c in casts" :key="c.id">
              <!-- mainCastIds は配列 -->
              <input  class="btn-check"
                      type="checkbox"
                      :id="`main-${c.id}`"
                      :value="c.id"
                      v-model="mainCastIds">
              <label  class="btn"
                      :class="mainCastIds.includes(c.id)
                              ? 'btn-danger'
                              : 'btn-outline-danger'"
                      :for="`main-${c.id}`">
                {{ c.stage_name }}
              </label>
            </template>
          </div>
        </div>

        <!-- ===================== フリータブ ===================== -->
        <div v-else class="mb-3">
          <div class="d-flex flex-wrap gap-2">
            <template v-for="c in casts" :key="c.id">
              <!-- 本指名と重複しないよう disabled -->
              <input  class="btn-check"
                      type="checkbox"
                      :id="`free-${c.id}`"
                      :value="c.id"
                      v-model="freeCastIds"
                      :disabled="mainCastIds.includes(c.id)">
              <label  class="btn"
                      :class="freeCastIds.includes(c.id)
                              ? 'btn-primary'
                              : 'btn-outline-primary'"
                      :for="`free-${c.id}`">
                {{ c.stage_name }}
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
            style="grid-template-columns: 40% 40% 10% auto;">

          <!-- ① 注文キャスト -->
          <select class="form-select" v-model="draftCastId">
            <option :value="null">‑ CAST ‑</option>
            <option v-for="c in casts" :key="c.id" :value="c.id">{{ c.stage_name }}</option>
          </select>

          <!-- ② 品名 -->
          <select class="form-select" v-model="draftMasterId">
            <option :value="null">‑ ITEM ‑</option>
            <option v-for="m in drinkMasters" :key="m.id" :value="m.id">{{ m.name }}</option>
          </select>

          <!-- ③ 数量 -->
          <input type="number" min="1"
                class="form-control text-end"
                v-model.number="draftQty">

          <!-- ④ 追加ボタン -->
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
            <!-- ★ masters で検索に変更 -->
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

