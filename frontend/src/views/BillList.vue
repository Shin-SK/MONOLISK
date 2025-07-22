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

/* ───── 一覧ヘルパ関数（テンプレートから呼ぶ） ───── */
function setName(b){
  for (const it of (b.items || [])) {
    /* 日本語パターン「セット60分」 */
    if (/^セット\d+分/.test(it.name)) return it.name
    /* ラテン表記「set60」「SET60」など → 60 を抜き出して整形 */
    const m = it.name.match(/^set(\d+)/i)
    if (m) return `セット${m[1]}分`
  }
  return '‑'
}

function calcOut(b){
  if (!b.opened_at) return '‑'
  let minutes = 0
  ;(b.items || []).forEach(it => {
    /* セット */
    let m = it.name.match(/^セット(\d+)分/) || it.name.match(/^set(\d+)/i)
    if (m) { minutes += +m[1]; return }

    /* 延長 */
    if (/延長/.test(it.name) || /^ext\d+/i.test(it.name)){
      const mExt = it.name.match(/(\d+)分/) || it.name.match(/^ext(\d+)/i)
      minutes += mExt ? +mExt[1] : 30   // 分数不明なら既定 30 分
    }
  })
  return minutes
    ? dayjs(b.opened_at).add(minutes,'minute').format('HH:mm')
    : '‑'
}

function extStats(b){
  let count = 0, totalMin = 0
  ;(b.items || []).forEach(it => {
    if (/延長/.test(it.name) || /^ext\d+/i.test(it.name)){
      count++
      const m = it.name.match(/(\d+)分/) || it.name.match(/^ext(\d+)/i)
      totalMin += m ? +m[1] : 30
    }
  })
  return { count, totalMin }
}

function liveCasts(b){
  return (b.stays||[])
    .filter(s=>!s.left_at)
    .map(s=>{
      const cid = s.cast?.id
      let tag='', color=''
      if(cid === (b.nominated_casts?.[0]||null)){ tag='本指名'; color='danger'}
      else if((b.inhouse_casts||[]).includes(cid)){ tag='場内'; color='success'}
      return {
        id:cid,
        name:s.cast?.stage_name||'N/A',
        avatar:s.cast?.avatar_url||'/img/user-default.png',
        tag, color
      }
    })
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

