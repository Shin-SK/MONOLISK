<!-- BillLitTable.vue -->
<script setup>
import { ref, onMounted, computed } from 'vue'
import dayjs from 'dayjs'
import { useBills }  from '@/stores/useBills'
import BillModal     from '@/components/BillModal.vue'
import Avatar        from '@/components/Avatar.vue'
import { fetchBill, createBill, fetchTables } from '@/api'

/* ── state ── */
const billsStore  = useBills()
const tables      = ref([])
const showModal   = ref(false)
const currentBill = ref(null)

/* ── 初回ロード ── */
onMounted(async () => {
  await Promise.all([billsStore.loadAll(), loadTables()])
})

async function loadTables () {
  tables.value = await fetchTables()
}

/* ── 時間トリガ（1 分ごと） ───────────────── */
const tick = ref(Date.now())
setInterval(() => (tick.value = Date.now()), 60_000)

function paxCount (bill){
  if(!bill) return null
  const setItem = (bill.items || []).find(i => i.code?.startsWith('set'))
  return setItem ? setItem.qty : null        // SET が無ければ null
}

/* ── tableId → open‑bill マップ ── */
const openBillMap = computed(() => {
  const m = new Map()
  billsStore.list.forEach(b => {
     if (
       !b.closed_at &&
       dayjs(b.opened_at).isSame(dayjs(), 'day')   // ★ 今日の伝票だけ！
     ){
       m.set(b.table?.id || b.table, b)
     }  })
  return m
})
function getOpenBill (tableId) {
  return openBillMap.value.get(tableId) || null
}

/* ── カードクリック ── */
async function handleClick (table) {
  const hit = getOpenBill(table.id)

  if (hit){
    currentBill.value = await fetchBill(hit.id)   // 既存伝票 → そのまま
  }else{
    const bill = await createBill({ table_id: table.id })
    // table.number をモーダルに渡すため、オブジェクトを合成
    currentBill.value = { ...bill, table }       // table は {id,number,store}
  }

  showModal.value = true
}

/* モーダル保存後 */
async function handleSaved () {
  showModal.value = false
  await billsStore.loadAll()
}

/* 新規追加ボタン（テーブル未指定） */
async function newBill () {
  currentBill.value = await createBill({ table_id: null })
  showModal.value   = true
}


/* キャスト一覧 */
function liveCasts(b){
  /* 再レンダー用に参照 */
  tick.value

  /* free 色＆下線幅を計算 */
  const freeProps = (stay)=>{
    const mins   = dayjs(tick.value).diff(dayjs(stay.entered_at),'minute')
    const color  = mins>=30 ? 'orange'
               : mins>=20 ? 'orange'
               : mins>=10 ? 'warning'
               : 'blue'
    /* 0‑9 →10‑100%, 10‑19 →10‑100%, … */
    const within = mins%10
    const width  = `${Math.min(within+1,10)*10}%`
    return { color, width }
  }

  return (b.stays||[])
    .filter(s=>!s.left_at)
    .map(s=>{
      if(s.stay_type==='free'){
        const {color,width} = freeProps(s)
        return {
          id:s.cast?.id, name:s.cast?.stage_name||'N/A',
          avatar:s.cast?.avatar_url||'/img/user-default.png',
          color, afterWidth: width
        }
      }
      return {
        id:s.cast?.id, name:s.cast?.stage_name||'N/A',
        avatar:s.cast?.avatar_url||'/img/user-default.png',
        color: s.stay_type==='nom'?'danger':'success'
      }
    })
}

</script>

<template>
  <header class="d-flex justify-content-between">
    <div class="d-flex gap-1 mt-5 mb-2">
      <span class="badge bg-danger">本指名</span>
      <span class="badge bg-success">場内</span>
      <span class="badge bg-blue">フリー(~10分)</span>
      <span class="badge bg-warning">フリー(~20分)</span>
      <span class="badge bg-orange">フリー(~30分)</span>
    </div>
    <button class="btn btn-success align-items-center gap-1 mb-3"
            @click="newBill">
      <i class="bi bi-plus-lg"></i> 新規追加
    </button>
  </header>

  <!-- ★ テーブル基準でカード生成 -->
  <div class="tables d-grid gap-4">
    <template v-for="t in tables" :key="t.id">
      <!-- 伝票あり -->
      <div v-if="getOpenBill(t.id)"
           class="table-box bg-white rounded"
           @click="handleClick(t)" style="cursor:pointer">
        <div class="header rounded-top d-flex gap-3 bg-dark text-light py-2 px-4 align-items-center">
          <div class="item fs-4"><i class="bi bi-geo-fill"></i>{{ t.number }}</div>
          <div class="item ms-auto"><i class="bi bi-journal"></i>{{ getOpenBill(t.id).id }}</div>
          <div class="item"><i class="bi bi-person-fill"></i>{{ paxCount(getOpenBill(t.id)) ?? '‑' }}</div>
          <div class="item">{{ getOpenBill(t.id).set_rounds || '‑' }}SET</div>
        </div>

        <div class="content p-3 d-flex flex-column h-100">
          <div class="casts d-flex flex-wrap gap-2 mb-3">
            <div v-for="p in liveCasts(getOpenBill(t.id))" :key="p.id"
                 class="d-flex align-items-center btn text-light p-2"
                 :class="`bg-${p.color}`"
                 :style="p.afterWidth ? {'--after-width': p.afterWidth} : {}">
              <Avatar :url="p.avatar" :alt="p.name" size="28" class="me-1"/>
              <span class="fw-bold">{{ p.name }}</span>
            </div>
          </div>

          <div class="time fs-2 mt-auto d-flex gap-2 align-items-center">
            <span class="fs-5 me-1"><i class="bi bi-clock"></i></span>
            <span class="fw-bold">
              {{ dayjs(getOpenBill(t.id).opened_at).format('HH:mm') }}
            </span> -
            <span class="fw-bold">
              {{ getOpenBill(t.id).expected_out
                   ? dayjs(getOpenBill(t.id).expected_out).format('HH:mm')
                   : '‑' }}
            </span>
          </div>
          <!-- ── 金額 ── -->
          <div class="sum d-flex gap-4 mt-2">
            <div class="item">
              <span class="badge bg-secondary">小計</span>
              <span>{{ getOpenBill(t.id).subtotal.toLocaleString() }}</span>
            </div>
            <div class="item">
              <span class="badge bg-secondary">合計</span>
              <span class="fw-bold">
                {{
                  (
                    getOpenBill(t.id).settled_total
                    ?? (getOpenBill(t.id).closed_at
                          ? getOpenBill(t.id).total
                          : getOpenBill(t.id).grand_total)
                  ).toLocaleString()
                }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空席 -->
      <div v-else class="table-box bg-light rounded d-flex flex-column
                         justify-content-center align-items-center"
           @click="handleClick(t)" style="cursor:pointer">
        <div class="header rounded-top d-flex gap-2 bg-dark text-light py-2 px-4 align-items-center">
          <div class="item fs-4"><i class="bi bi-geo-fill"></i>{{ t.number }}</div>
        </div>
        <div class="content p-3 d-flex align-items-center justify-content-center h-100">
        <div class="text-muted fs-3">空席</div>
        </div>
      </div>
    </template>
  </div>

  <!-- モーダル -->
  <BillModal v-model="showModal"
             :bill="currentBill"
             @saved="handleSaved"/>
</template>

<style scoped>

.casts .btn{
  position:relative;
}
.casts .btn::after{
  content:'';
  position:absolute;
  left:0; bottom:2px;
  height:2px;                       /* 線の太さ */
  width:var(--after-width,0);       /* free だけ動的 */
  background:currentColor;
  transition:width .2s linear;
}
</style>
