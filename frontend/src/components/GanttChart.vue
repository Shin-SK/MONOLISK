<script setup>
/* ───────── imports ───────── */
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import dayjs from 'dayjs'
import { fetchTables, fetchBills } from '@/api'

/* ───────── props ───────── */
const props = defineProps({
  date          : { type:String, default: dayjs().format('YYYY-MM-DD') },
  startHour     : { type:Number,  default: 0 },
  hoursPerChart : { type:Number,  default: 24 },
  storeId       : { type:[Number,String], default:null },
})

/* ───────── chart 範囲 ───────── */
const chartStart = computed(() =>
  dayjs(props.date).hour(props.startHour).minute(0).second(0).toDate()
)
const chartEnd = computed(() =>
  dayjs(chartStart.value).add(props.hoursPerChart, 'hour').toDate()
)

/* ───────── state ───────── */
const rows = ref([])   // [{id,label}]
const bars = ref([])   // [{rowId,from,to,stays,billId,ganttBarConfig}]

/* ★追加：内部フラグ */
let firstCenterDone = false

/* ───────── stay → バッジ class ───────── */
function badgeClass (stay){
  if (stay.stay_type==='nom') return 'bg-danger'
  if (stay.stay_type==='in')  return 'bg-success'
  return '' // freeはfreePropsで入れる
}

/* ───────── 1 分ごとに色更新 ───────── */
const tick = ref(Date.now())
setInterval(()=>tick.value=Date.now(),60_000)

function freeProps (stay) {
  const mins   = dayjs(tick.value).diff(dayjs(stay.entered_at), 'minute')

  /* 30分超えは強制的にステージ2／幅100% に丸める */
  if (mins >= 30) {
    return { cls: 'bg-orange', width: '100%' }
  }

  /* 0‑29 分までは 10 分単位で段階色＋下線伸ばし */
  const stage   = Math.floor(mins / 10)          // 0,1,2
  const within  = mins % 10                      // 0‑9
  const color   = stage === 0 ? 'blue'      // 青
                : stage === 1 ? 'warning'        // 黄
                :               'orange'         // 20‑29 分
  return {
    cls  : `bg-${color}`,
    width: `${(within + 1) * 10}%`               // 10% → 100%
  }
}


/* ───────── 行取得 ───────── */
async function fetchRows(){
  const tables = await fetchTables(props.storeId || undefined)
  rows.value = tables
    .sort((a,b)=>a.number-b.number)
    .map(t=>({ id:t.id, label:`${t.number}` }))
}

/* ───────── バー取得 ───────── */
async function fetchBars(){
  const bills = await fetchBills(props.storeId ? { store:props.storeId } : {})
  bars.value = bills
    .map(b=>{
      if(!b.table) return null      // table 未設定は除外

      const rowId = typeof b.table==='object' ? b.table.id : b.table
      const from  = new Date(b.opened_at)
      const to = b.expected_out               // ← 常に期待退店で描画
        ? new Date(b.expected_out)
        : new Date()                          // 念のためフォールバック

      const isClosed = !!b.closed_at          // ← フラグ立てる

      return {
        rowId,
        from,
        to,
        billId : b.id,
        stays  : b.stays || [],
        ganttBarConfig:{
          id   : `bill_${b.id}`,
          label: '',
          style:{ background: isClosed
                  ? 'rgba(108,117,125,.3)'     // ← グレーで「済」
                  : 'rgba(25,135,84,.2)' }     // ← 営業中は従来色
        },
        isClosed,
      }
    })
    .filter(Boolean)
}

/* ───────── まとめて更新 ───────── */
async function refresh(){ await fetchRows(); await fetchBars(); nextTick(resizeAll) }
watch(()=>[props.date,props.storeId], refresh, { immediate:true })

/* ───────── now‑line ───────── */
const nowX = ref(0)
const wrapperRef = ref(null)

/* ★追加：now線を中央に寄せる */
function centerNow () {
	const el = wrapperRef.value
	if (!el) return
	// now線を画面中央に置くための scrollLeft を計算
	const target = Math.max(0, nowX.value - el.clientWidth / 2)
	el.scrollLeft = Math.min(target, el.scrollWidth - el.clientWidth)
}

function recalcNow(){
	const total = chartEnd.value - chartStart.value
	nowX.value  = ((Date.now()-chartStart.value)/total)*wrapperRef.value.scrollWidth

	/* ★追加：初回だけ中央寄せ */
	if (!firstCenterDone) {
		nextTick(centerNow)
		firstCenterDone = true
	}
}
setInterval(recalcNow, 60_000)

/* ───────── グリッド & 横スクロール幅 ───────── */
const pxPerMinute = ref(6)
const gridStep    = computed(()=>pxPerMinute.value*10)

/* 1 画面で見せる時間幅（h） */
const hoursPerViewport = 4
const chartWidth = computed(
  () => `${(props.hoursPerChart / hoursPerViewport) * 100}%`
)

function recalcPx(){
  const el = wrapperRef.value
  if(!el) return
  pxPerMinute.value = el.scrollWidth/(props.hoursPerChart*60)
}
function resizeAll(){ nextTick(()=>{ recalcPx(); recalcNow() }) }
window.addEventListener('resize',()=>nextTick(resizeAll))
watch([chartStart,chartEnd],()=>nextTick(resizeAll))

/* ───────── emit ───────── */
const emit = defineEmits(['bill-click','request-new'])
function onBarClick({ bar }) { emit('bill-click',{ billId:bar.billId }) }

/* 空行クリック → 新規伝票 */
function onRowClick(e,rowId){
  if(e.target.closest('.g-gantt-bar')) return
  emit('request-new',{ tableId:rowId })
}

/* ───────── expose ───────── */
defineExpose({ reload: refresh })
onMounted(() => {
	resizeAll()
	/* ★追加：DOM サイズ確定後に中央寄せ */
	nextTick(() => {
		recalcNow()   // nowX 更新
		centerNow()   // 明示的に中央寄せ
	})
})
</script>

<template>
<div class="gc-wrapper" style="overflow-x:auto;">
  <div class="gantt-board">
    <!-- テーブル列 -->
    <div class="label-col">
      <div v-for="row in rows" :key="row.id" class="label-row">
        <span class="label-label">{{ row.label }}</span>
      </div>
    </div>

    <!-- チャート -->
    <div class="chart-col" ref="wrapperRef" :style="{'--grid-step': gridStep + 'px'}">
      <div class="now-line" :style="{left: nowX + 'px'}"></div>

      <g-gantt-chart
        :chart-start="chartStart"
        :chart-end="chartEnd"
        :row-height="40"
        precision="hour"
        :precision-step="10"
        :width="chartWidth"
        bar-start="from"
        bar-end="to"
        push-on-overlap
        @click-bar="onBarClick"
        :style="{ '--grid-step': gridStep + 'px' }"
      >
        <g-gantt-row
          v-for="row in rows"
          :key="row.id"
          :bars="bars.filter(b=>b.rowId===row.id)"
          @click="e=>onRowClick(e,row.id)"
        >
          <template #bar-label="{ bar }">
            <span v-for="stay in bar.stays"
                  :key="stay.cast.id"
                  class="badge"
                  :class="stay.stay_type==='free' ? freeProps(stay).cls : badgeClass(stay)"
                  :style="stay.stay_type==='free'
                          ? { '--after-width': freeProps(stay).width }
                          : {}">
              {{ stay.cast.stage_name }}
            </span>
          </template>
        </g-gantt-row>
      </g-gantt-chart>
    </div>
  </div>
</div>
</template>

<style scoped>
/* --- 基本スタイル（バッジは Bootstrap に任せる） --- */
.g-gantt-bar{ position:relative; border-radius:4px; font-size:11px; cursor:grab }

/* グリッド線 */
:deep(.g-gantt-chart){ position:relative; background:transparent }
:deep(.g-gantt-chart)::before{
  content:''; position:absolute; inset:0;
  background-image:linear-gradient(to right,rgba(0,0,0,.1) 1px,transparent 1px);
  background-size:var(--grid-step) 100%; pointer-events:none; z-index:0;
}

/* 現在時刻ライン */
.chart-col{ position:relative }
.now-line{ position:absolute; top:0; bottom:0; width:1px; background:red; opacity:.5; z-index:2 }

/* 上段ラベルを消す */
:deep(.g-upper-timeunit){ display:none }
:deep(.g-gantt-chart){ margin-top:-40px }
:deep(.g-gantt-row){ position:relative }

/*  badge下のステータス線 */
.badge{
  position: relative;
}

.badge::after{
  content:'';
  position:absolute;
  left:0;
  bottom:1px;
  height:1px;                /* 線の太さ */
  width:var(--after-width);  /* ← ここを追加 */
  background:currentColor;   /* バッジと同じ色 */
  transition:width .2s linear;
}

</style>
