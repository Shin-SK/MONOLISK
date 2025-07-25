<!-- views/BillList.vue -->
<script setup>
/* ───── Imports ───── */
import { ref, onMounted, computed } from 'vue'
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

/* 任意：同じ日か判定するだけ */
function isSameDay(d1, d2){
  if (!d1 || !d2) return false
  return dayjs(d1).isSame(d2, 'day')
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
             : 'blue'
    }))
}

</script>




<template>
  <header class="d-flex justify-content-between">
    <div class="d-flex gap-1 mt-5 mb-2">
        <div class="item badge text-white bg-danger">本指名</div>
        <div class="item badge text-white bg-success">場内</div>
        <div class="item badge text-white bg-blue">フリー(~10分)</div>
        <div class="item badge text-white bg-warning">フリー(~20分)</div>
        <div class="item badge text-white bg-orange">フリー(~30分)</div>
    </div>
    <button class="btn btn-primary d-flex align-items-center gap-1 mb-3"
            @click="newBill">
      <i class="bi bi-plus-lg"></i> 新規追加
    </button>
  </header>
  
  <table class="bill-table table table-bordered table-hover align-middle table-striped" style="table-layout: fixed;">
      <colgroup>
        <col style="width:  40px">  <!-- チェック -->
        <col style="width:  40px">  <!-- ID -->
        <col style="width:  40px">  <!-- 卓 -->
        <col style="width:  40px">  <!-- SET -->
        <col style="width:  80px">  <!-- in -->
        <col style="width:  40px">  <!-- 延長 -->
        <col style="width:  80px">  <!-- out -->
        <col style="width: auto">   <!-- ★ キャスト：残り全部 -->
        <col style="width: 160px">  <!-- 小計 -->
        <col style="width: 160px">  <!-- 合計 -->
      </colgroup>
      <thead>
      <tr>
        <th></th>
        <th class="text-center">ID</th>
        <th class="text-center">卓</th>
        <th class="text-center">SET</th>
        <th class="text-center">in</th>
        <th class="text-center">延長</th>
        <th class="text-center">out</th>
        <th class="text-center">キャスト</th>
        <th class="text-end">小計</th>
        <th class="text-end">合計</th>
      </tr>
    </thead>
    <tbody>
      <template v-for="(b, idx) in bills.list" :key="b.id">
        <!-- ★ 見出し行：前の伝票と日付が違えば出力 -->
        <tr v-if="idx === 0 || !isSameDay(bills.list[idx-1].opened_at, b.opened_at)"
            class="bg-light">
          <td :colspan="10" class="text-center fw-bold">
            {{ b.opened_at ? dayjs(b.opened_at).format('YYYY/MM/DD(ddd)') : '日付未定' }}
          </td>
        </tr>
      <tr @click="open(b.id)" style="cursor:pointer" class="main">
        <td class="text-center">
          <input type="checkbox"
                 :value="b.id"
                 :checked="selectedIds.has(b.id)"
                 @click.stop="toggle(b.id)">
        </td>
        <td class="text-center">{{ b.id }}</td>
        <td class="text-center">{{ b.table?.number ?? '‑' }}</td>
        <td class="text-center">{{ b.set_rounds || '‑' }}</td>
        <td class="text-center">
            <span class="fs-3 fw-bold">
            {{ b.opened_at ? dayjs(b.opened_at).format('HH:mm') : '‑' }}
          </span>
        </td>
        <td class="text-center">
          <span>{{ b.ext_minutes ? Math.floor(b.ext_minutes/30) : '‑' }}</span>
        </td>
        <td class="text-center"><span class="fs-3 fw-bold">{{ b.expected_out ? dayjs(b.expected_out).format('HH:mm') : '‑' }}</span></td>
			
      <td>
        <div class="d-flex flex-wrap gap-2">
          <div v-for="p in liveCasts(b)" :key="p.id"
            class="d-flex align-items-center btn text-light p-2"
            :class="`bg-${p.color}`">
            <img :src="p.avatar" class="avatar-icon me-1" width="40" height="40">
            <div class="wrap d-flex flex-column align-items-start">
              <span class="fw-bold">{{ p.name }}</span>
            </div>
          </div>
        </div>
      </td>
        <td class="text-end">{{ b.subtotal.toLocaleString() }}</td>
        <td class="text-end">{{ (b.settled_total ?? (b.closed_at ? b.total : b.grand_total)).toLocaleString() }}</td>
      </tr>
    </template>
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

<style scoped>

tr.main td{
  padding:16px 4px;
}


</style>