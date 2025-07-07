<!-- components/GanttChart.vue -->
<script setup>
/* ───────── 依存 ───────── */
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import dayjs from 'dayjs'
import { getCastProfiles, getReservations, getDrivers } from '@/api'
import { Tooltip } from 'bootstrap'

/* ───────── props ───────── */
const props = defineProps({
  date         : { type:String, default: dayjs().format('YYYY-MM-DD') },
  beforeMinutes: { type:Number, default: 20 },
  afterMinutes : { type:Number, default: 30 },
  storeId      : { type:[Number,String], default: null },
  startHour       : { type:Number,  default: 0  },   // ← 追加 (0-23)
  hoursPerChart   : { type:Number,  default: 24 },
})

/* ───────── state ───────── */
const rows     = ref([])      // 行 [{id,label}]
const bars     = ref([])      // バー
const castMap  = ref({})      // { castId: stage_name }
const driverMap = ref({}) 

/* ───────── util ───────── */
const driverName = (r, role) => {
  const list = r.reservation_drivers ?? r.drivers ?? []
  const found = list.find(d => d.role === role)
  if (!found) return ''

  // ① 既にオブジェクトならそのまま
  if (typeof found.driver === 'object') {
    return found.driver.name || found.driver.driver_name || ''
  }

  // ② 数値 id なら driverMap で引く
  return driverMap.value[found.driver] || ''
}


/* ───────── 色 ───────── */

const PALETTE = [
  { max:  60, color: '#7bbef5' }, // blue
  { max:  75, color: '#00D7D4' }, // cyan
  { max:  90, color: '#4CAF50' }, // green
  { max: 120, color: '#CDDC39' }, // yellow-lime
  { max: 150, color: '#FF9800' }, // orange
  { max: 180, color: '#FF4081' }, // pink
  { max: Infinity, color: '#9C27B0' } // purple (pack)
]

function colorForMinutes(mins) {
  return PALETTE.find(p => mins <= p.max).color
}

/* ───────── fetch rows ───────── */
async function fetchRows () {
  const casts = await getCastProfiles({ store: props.storeId || undefined })

  rows.value = casts.map(c => {
   // 既定があればそれ、なければ 1 件目
   const primary = c.standby_places?.find(p => p.is_primary) ?? c.standby_places?.[0]

    return {
      id   : c.id,
      label: c.stage_name || c.name || 'CAST',
      place: primary?.label || '' ,
      placeAddr: primary?.address || ''
    }
  })

  castMap.value = Object.fromEntries(
    casts.map(c => [c.id, c.stage_name || c.name || 'CAST'])
  )
}

const EXTEND_COLOR = 'rgba(255,0,0,.65)'   // 半透明の赤


/* ───────── ステータス辞書 ───────── */
const STATUS_META = {
  CALL_PENDING : { short:'確未',  color:'#6c757d' }, // secondary
  CALL_DONE    : { short:'確済',  color:'#0dcaf0' }, // info
  BOOKED       : { short:'仮予',  color:'#ffc107' }, // warning
  IN_SERVICE   : { short:'接中',  color:'#198754' }, // success
  CASH_COLLECT : { short:'集済',  color:'#0d6efd' }, // primary
}
const statusColorHex = s => STATUS_META[s]?.color || '#ced4da' /* fallback */

const statusShort = s => STATUS_META[s]?.short || s
const statusColor = s => STATUS_META[s]?.color || 'bg-light'

const statusBorder = s =>
  (STATUS_META[s]?.color || 'bg-light')      // 例) bg-warning
    .replace('bg-', 'border-')               // → border-warning



/* ───────── Bars ───────── */
async function fetchBars () {
  const reservations = await getReservations({
    date   : props.date,
    store  : props.storeId || undefined,
    ordering: 'start_at'
  })

  const list = reservations.flatMap(r =>
    r.casts.flatMap((rc, idx) => {
      const castId  = typeof rc.cast_profile === 'object'
                      ? rc.cast_profile.id : rc.cast_profile

      const baseMin  = rc.minutes           // minutes フィールド優先
                    ?? rc.course?.minutes    // 念のため
                    ?? r.total_time          // 最後の逃げ
      const extMin  = Math.max(0, (r.total_time ?? baseMin) - baseMin)

      const st  = dayjs(r.start_at)
      const ed  = st.add(baseMin, 'minute')
      const bars = []

      // 元コース
      bars.push({
        rowId : castId,
        from  : st.toDate(),
        to    : ed.toDate(),
        reservationId: r.id,
        puName: driverName(r,'PU') || '',
        doName: driverName(r,'DO') || '',
        status: r.status, 
        address: r.pickup_address || '', 
        ganttBarConfig: {
          id   : `r${r.id}_${idx}_main`,
          label: `${statusShort(r.status)} ${r.pickup_address||''}`,
          style: {
            '--pu-px': `${props.beforeMinutes*2}px`,
            '--do-px': `${props.afterMinutes*2}px`,
            borderBottom  : `3px solid ${statusColorHex(r.status)}`,
            background: colorForMinutes(baseMin)
          }
        }
      })

      // 延長セグメント
      if (extMin > 0) {
        const extEnd = ed.add(extMin, 'minute')
        bars.push({
          rowId: castId,
          from : ed.toDate(),
          to   : extEnd.toDate(),
          reservationId: r.id,
          isExtend: true,
          ganttBarConfig: {
            id   : `r${r.id}_${idx}_ext`,
            label: `延長 ${extMin}min`,
            style: { background: EXTEND_COLOR }
          }
        })
      }

      return bars
    })
  )

  // 生成した配列を reactive 変数へ流し込む
  bars.value = list
  }


/* ───────── ドライバー系 ───────── */
async function fetchDrivers () {
  const list = await getDrivers()
  driverMap.value = Object.fromEntries(
    list.map(d => [d.id, d.name || d.driver_name || 'DRV'])
  )
}
onMounted(fetchDrivers)

/* Tooltip を毎回張り直す util */
function enableTooltips () {
  nextTick(() => {
    document
      .querySelectorAll('[data-bs-toggle="tooltip"]')
      .forEach(el => {
        // 既にある場合は再利用
        Tooltip.getOrCreateInstance(el, {
          container : 'body',   // ← 親の overflow を無視して body に
          trigger   : 'hover',
        })
      })
  })
}

/* ───────── helper: まとめて更新 ───────── */
async function refresh () {
  await fetchRows()   // キャスト → 行 / map
  await fetchBars()   // それを使ってバー生成
}

/* ───────── watch & 初期化 ───────── */
watch(() => [props.date, props.storeId], refresh, { immediate:true })
onMounted(refresh)

/* ───────── chart 範囲 ───────── */
const chartStart = computed(() =>
  dayjs(props.date)
    .hour(props.startHour).minute(0).second(0).toDate()
)

const chartEnd = computed(() =>
  dayjs(chartStart.value)
    .add(props.hoursPerChart, 'hour').toDate()
)

/* ───────── emit ───────── */
const emit = defineEmits(['update','bar-click'])

function onDragEnd({ bar }) {
  emit('update', {
    reservationId: bar.reservationId,
    newStartISO  : dayjs(bar.from).toISOString()
  })
}

function onBarClick({ bar }) {
  emit('bar-click', { reservationId: bar.reservationId })
}

/* ───────── リロード ───────── */

async function reload () {
  await refresh()      // rows と bars を一括生成
}

defineExpose({ reload })

/* ───────── 描画 ───────── */

const hoursPerViewport = 6                     // 例: 1画面に16h見せる
const chartWidth = computed(
  () => `${(props.hoursPerChart / hoursPerViewport) * 100}%`
)

const rowHeight = 40

const wrapperRef = ref(null)

function centerNow () {
  const el = wrapperRef.value
  if (!el) return
  const total   = chartEnd.value.getTime() - chartStart.value.getTime()
  const elapsed = Date.now()               - chartStart.value.getTime()
  const ratio   = Math.min(1, Math.max(0, elapsed / total))
  el.scrollLeft = ratio * el.scrollWidth - el.clientWidth / 2
}


onMounted(enableTooltips)
/* rows / address が変わるたびに再初期化 */
watch(rows, enableTooltips, { deep: true })
watch([rows, bars, chartStart, chartEnd], () => nextTick(centerNow))
</script>




<template>
  <div class="gc-wrapper" style="overflow-x:auto;">

  <div class="gantt-board">
    <!-- 固定キャスト列 -->
    <div class="label-col">
      <div
        v-for="row in rows"
        :key="row.id"
        class="label-row"
      >
      <span class="label-label">
        <span class="d-block">{{ row.label }}</span>

        <!-- ① data-bs-title に住所、② data-bs-toggle="tooltip" -->
        <span
          v-if="row.place"
          class="badge bg-light text-dark"
          data-bs-toggle="tooltip"
          data-bs-placement="right"
          data-bs-container="body"
          data-bs-boundary="window"
          data-bs-custom-class="tp-light"
        >
          {{ row.place }}
        </span>
      </span>
      </div>
    </div>

    <!-- チャート側（横だけスクロール） -->
    <div class="chart-col" ref="wrapperRef">
      <!-- ★ g-gantt-chart はそのまま -->
      <g-gantt-chart
        :chart-start="chartStart"
        :chart-end="chartEnd"
        :row-height="rowHeight"
        :width="chartWidth"
        bar-start="from"
        bar-end="to"
        precision="hour"
        :precision-step="5"
        push-on-overlap
        @dragend-bar="onDragEnd"
        @click-bar="onBarClick"
      >
        <g-gantt-row
          v-for="row in rows"
          :key="row.id"
          :bars="bars.filter(b => b.rowId === row.id)"
        >
        <template #bar-label="{ bar }">
          <span v-if="bar.puName" class="drv-label left">{{ bar.puName }}</span>

          <!-- 住所：幅制限＆ellipsis、hover で全文 -->
          <span class="addr-text">
            {{ bar.address }}
          </span>

          <span v-if="bar.doName" class="drv-label right">{{ bar.doName }}</span>
        </template>
        </g-gantt-row>
      </g-gantt-chart>
    </div>
  </div>
  </div>
</template>

<style scoped>

/* Main バー自体 */
.g-gantt-bar {
  position: relative;
  border-radius: 4px;
  cursor: grab;
  font-size: 11px;
  /* 疑似要素を収めるため padding を確保しても OK */
}

/* scoped 内に追加 */
.g-gantt-bar[style*="rgba(255,0,0"] {
  opacity: .7;          /* 好みで */
}

/* light style のツールチップ本体 */
.tp-light .tooltip-inner {
  background-color: var(--bs-light);
  color: var(--bs-dark);
  border: 1px solid var(--bs-border-color-translucent);
}

/* 矢印部分 */
.tp-light .tooltip-arrow::before {
  background-color: var(--bs-light);
  /* ↑ “::after” になる場合もあるので環境に合わせて調整 */
}

.tooltip.show{
  color: white !important;
}
</style>