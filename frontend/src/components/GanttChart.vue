<!-- components/GanttChart.vue -->
<script setup>
/* ───────── 依存 ───────── */
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import dayjs from 'dayjs'
import { getCastProfiles, getReservations, getDrivers } from '@/api'

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
  { max:  60, color: '#2294F2' }, // blue
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

  rows.value = casts.map(c => ({
    id   : c.id,
    label: c.stage_name || c.name || 'CAST'
  }))

  castMap.value = Object.fromEntries(
    casts.map(c => [c.id, c.stage_name || c.name || 'CAST'])
  )
}

/* ───────── fetch bars ───────── */
// async function fetchBars () {
//   const reservations = await getReservations({
//     date    : props.date,
//     store   : props.storeId || undefined,
//     ordering: 'start_at'
//   })

//   const list = reservations.flatMap(r =>
//     r.casts.map((rc, idx) => {
//       const castId = typeof rc.cast_profile === 'object'
//                      ? rc.cast_profile.id : rc.cast_profile

//       const stage = castMap.value[castId] ?? 'CAST'
//       const st    = dayjs(r.start_at)
//       const mins  = rc.course?.minutes ?? r.total_time ?? 60
//       const ed    = st.add(mins,'minute')


//       /* バッファ用幅を px に換算（例: 1 分 = 2px） */
//       const puPx = props.beforeMinutes * 2
//       const doPx = props.afterMinutes  * 2

//       return {
//         rowId: castId,
//         from : st.toDate(),
//         to   : ed.toDate(),
//         ganttBarConfig: {
//           id   : `r${r.id}_${idx}_main`,
//           label: `${stage} / #${r.id} (PU:${driverName(r,'PU')}, DO:${driverName(r,'DO')})`,
//           style: {
//             '--pu-px': `${puPx}px`,
//             '--do-px': `${doPx}px`,
//             background: colorForMinutes(mins)   // ←ここを差し替え
//           }
//         },
//         reservationId: r.id,
//         puName : driverName(r, 'PU')  || '',   // ←★
//         doName : driverName(r, 'DO') || '',   // ←★
//       }
//     })
//   )

//   bars.value = list
// }

const EXTEND_COLOR = 'rgba(255,0,0,.65)'   // 半透明の赤

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
        ganttBarConfig: {
          id   : `r${r.id}_${idx}_main`,
          label: `${castMap.value[castId] || 'CAST'} / #${r.id}`,
          style: {
            '--pu-px': `${props.beforeMinutes*2}px`,
            '--do-px': `${props.afterMinutes*2}px`,
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
onMounted(() => nextTick(centerNow))
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
          {{ row.label }}
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
            <span class="bar-center">#{{ bar.reservationId }}</span>
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

</style>