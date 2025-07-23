<!-- views/BillList.vue -->
<script setup>
/* ───── Imports ───── */
import { ref, onMounted } from 'vue'
import dayjs              from 'dayjs'          // ← 忘れずに
import { useBills }       from '@/stores/useBills'
import BillModal          from '@/components/BillModal.vue'
import { fetchBill, createBill, deleteBill } from '@/api'

/* ───── reactive state ───── */
const bills       = useBills()
const showModal   = ref(false)          // モーダル開閉フラグ
const currentBill = ref(null)          // モーダルに渡す 1 伝票
const selectedIds = ref(new Set())     // 一覧チェック用

/* ───── 初回ロード ───── */
onMounted(() => bills.loadAll())

const MAP_SET = { setVIP:60, setMale:60, setFemale:60, set60:60 }

/* ───── 一覧クリック → 1件取得してモーダル ───── */
async function open(id) {
  currentBill.value = await fetchBill(id)
  showModal.value   = true
}

/* ───── モーダル側から emit('saved') を受ける ───── */
function handleSaved() {
  showModal.value = false
  bills.loadAll()
}

/* ───── 新規伝票 ───── */
async function newBill () {
  const bill = await createBill({ table_id: 1, nominated_casts: [], inhouse_casts_w: [] })
  currentBill.value = bill
  showModal.value   = true
}

/* ───── 一覧チェック & 削除 ───── */
function toggle(id){
  const set = selectedIds.value
  set.has(id) ? set.delete(id) : set.add(id)
}

async function bulkDelete () {
  if (!selectedIds.value.size) return
  if (!window.confirm(`${selectedIds.value.size} 件を削除しますか？`)) return
  for (const id of selectedIds.value) await deleteBill(id)
  selectedIds.value.clear()
  bills.loadAll()
}

/* ---------- 伝票内ユーティリティ ---------- */

/* 1) その卓で最初に出た SET を返す */
function setName(b){
  for (const it of (b.items||[])){
    if (it.code?.startsWith('set')) {
      // duration_min が来ていれば優先、無ければコードごとに既定値
      const min =
        it.duration_min ??
        { setVIP:60, setMale:60, setFemale:60 }[it.code] ?? 60
      return `セット${min}分`
    }
  }
  return '‑'
}

/* 2) 退店予定時刻 (in + セット + 延長) */
function calcOut(b){
  if (!b.opened_at) return '‑'
  let minutes = 0
  ;(b.items||[]).forEach(it=>{
    if (it.code?.startsWith('set')) {
      minutes += (it.duration_min ??
                 { setVIP:60, setMale:60, setFemale:60 }[it.code] ?? 60) * it.qty
    }
    if (it.code?.startsWith('extension')) {
      minutes += (it.duration_min ??
                 { extensionVip:30, extension:30 }[it.code] ?? 30) * it.qty
    }
  })
  return minutes
    ? dayjs(b.opened_at).add(minutes,'minute').format('HH:mm')
    : '‑'
}

/* 3) 延長回数と合計分数 */
function extStats(b){
  let count = 0, totalMin = 0
  ;(b.items||[]).forEach(it=>{
    if (it.code?.startsWith('extension')){
      const min =
        it.duration_min ??
        { extensionVip:30, extension:30 }[it.code] ?? 30
      count   += it.qty
      totalMin+= min * it.qty
    }
  })
  return { count, totalMin }
}

function liveCasts(b){
  return (b.stays||[])
    .filter(s => !s.left_at)             // まだ席にいる人
    .map(s => ({
        id:      s.cast?.id,
        name:    s.cast?.stage_name || 'N/A',
        avatar:  s.cast?.avatar_url  || '/img/user-default.png',
        tag:   s.stay_type === 'nom' ? '本指名'
             : s.stay_type === 'in'  ? '場内'
             : '',
        color: s.stay_type === 'nom' ? 'danger'
             : s.stay_type === 'in'  ? 'success'
             : ''
    }))
}



</script>




<template>
    <button class="btn btn-primary d-flex align-items-center gap-1 mb-3"
            @click="newBill">
      <i class="bi bi-plus-lg"></i> 新規追加
    </button>
  <table class="table table-bordered table-hover align-middle table-striped">
    <thead>
      <tr>
        <th></th><th>ID</th><th>卓</th><th>in</th>
        <th>out</th><th>キャスト</th><th class="text-end">小計</th>
        <th class="text-end">合計</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="b in bills.list" :key="b.id"
          @click="open(b.id)" style="cursor:pointer">
        <td class="text-center">
          <input type="checkbox"
                 :value="b.id"
                 :checked="selectedIds.has(b.id)"
                 @click.stop="toggle(b.id)">
        </td>
        <td>{{ b.id }}</td>
        <td>{{ b.table?.number ?? '‑' }}</td>
        <td>
			<span class="badge bg-dark text-light">{{ setName(b) }}</span>
			<span class="fs-3 fw-bold d-block">{{ dayjs(b.opened_at).format('HH:mm') }}</span>
		</td>  <!-- タイムとセット -->
        <td>
			<!-- 延長 2 回 / 計 60 分 のように表示したい場合 -->
			<template v-if="extStats(b).count">
				<span class="badge bg-dark text-light">延長 {{ extStats(b).count }} 回</span>
			</template>
			<span class="fs-3 fw-bold d-block">{{ calcOut(b) }}</span>
		</td>                           <!-- out -->
			
		<td>
		<div class="d-flex flex-wrap gap-2">
			<div v-for="p in liveCasts(b)" :key="p.id"
				class="d-flex align-items-center btn btn-light p-2">
				<img :src="p.avatar" class="rounded-circle me-1" width="40" height="40">
				
				<div class="wrap d-flex flex-column align-items-start">
					<span v-if="p.tag" class="badge text-light"
							:class="`bg-${p.color}`">{{ p.tag }}</span>
					<span class="fw-bold">{{ p.name }}</span>
				</div>
			</div>
		</div>
		</td>
        <td class="text-end">{{ b.subtotal.toLocaleString() }}</td>
        <td class="text-end">{{ (b.settled_total ?? (b.closed_at ? b.total : b.grand_total)).toLocaleString() }}</td>
      </tr>
    </tbody>
  </table>

    <!-- ★ 削除ボタン -->
    <button class="btn btn-danger"
            :disabled="!selectedIds.size"
            @click="bulkDelete">
      <i class="bi bi-trash-fill"></i> 削除
    </button>

    <BillModal
      v-model="showModal"
      :bill="currentBill"
      @saved="handleSaved"
    />
</template>

