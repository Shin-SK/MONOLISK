<!-- components/GanttChart.vue -->
<script setup>
/* ───────── 依存 ───────── */
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import dayjs from 'dayjs'
import { getCastProfiles, getReservations, getDrivers, getShiftPlans } from '@/api'
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

/* ───────── chart 範囲（※最優先で宣言） ───────── */
const chartStart = computed(() =>
  dayjs(props.date).hour(props.startHour).minute(0).second(0).toDate()
)
const chartEnd = computed(() =>
  dayjs(chartStart.value).add(props.hoursPerChart, 'hour').toDate()
)

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

/* ───────── なう線 ───────── */

const nowX = ref(0)
function updateNow(){
  const total = chartEnd.value - chartStart.value
  nowX.value = ((Date.now()-chartStart.value)/total)*wrapperRef.value.scrollWidth
}
onMounted(()=>{ updateNow(); setInterval(updateNow,60000) })


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

const SHIFT_COLOR = 'rgba(111, 222, 111, .25)'   // 薄い緑（好みで）


/* ───────── fetch rows ───────── */
async function fetchRows () {
  // ① プロフィール & シフトを並列取得
  const [casts, shifts] = await Promise.all([
    getCastProfiles({ store: props.storeId || undefined }),
    getShiftPlans({ date: props.date, store: props.storeId || undefined })
  ])

  /* ---- シフト開始時刻を castId → dayjs インスタンスで保持 ---- */
  const shiftStartMap = Object.fromEntries(
    shifts.map(s => {
      const id   = s.cast_profile ?? s.cast_id        // 一応両方対応
      const from = dayjs(`${s.date}T${s.start_at}`)
      return [id, from]
    })
  )

  /* ---- rows を組み立て＋ソート ---- */
  rows.value = casts
    .map(c => {
      const primary = c.standby_places?.find(p => p.is_primary) ?? c.standby_places?.[0]
      return {
        id   : c.id,
        label: c.stage_name || c.name || 'CAST',
        place: primary?.label,
        placeAddr: primary?.address
      }
    })
    .sort((a, b) => {
      const sa = shiftStartMap[a.id]
      const sb = shiftStartMap[b.id]

      // ―― 両者ともシフトあり：開始時刻の早い順
      if (sa && sb) return sa - sb
      // ―― どちらかだけシフトあり：シフト有りを先頭に
      if (sa) return -1
      if (sb) return  1
      // ―― どちらもシフト無し：名前順（お好みで）
      return a.label.localeCompare(b.label, 'ja')
    })

  /* ---- castMap もそのまま保持 ---- */
  castMap.value = Object.fromEntries(
    casts.map(c => [c.id, c.stage_name || c.name || 'CAST'])
  )
}


const EXTEND_COLOR = 'rgba(255,0,0,.65)'   // 半透明の赤


/* ───────── ステータス辞書 ───────── */
const STATUS_META = {
  CALL_PENDING : { long:'電話確認[未]', short:'確未',  color:'#6c757d', badge : 'secondary' }, // secondary
  CALL_DONE    : { long:'電話確認[済]', short:'確済',  color:'#0dcaf0', badge : 'info'  }, // info
  BOOKED       : { long:'仮予約', short:'仮予',  color:'#ffc107', badge : 'warning' }, // warning
  IN_SERVICE   : { long:'接客中', short:'接中',  color:'#dc3545', badge : 'danger' }, // danger
  CASH_COLLECT : { long:'集金済', short:'集済',  color:'#0d6efd', badge : 'primary' }, // primary
}
const statusColorHex = s => STATUS_META[s]?.color || '#ced4da' /* fallback */

const statusShort = s => STATUS_META[s]?.short || s



/* ───────── グリッド線 ───────── */

// ▼ チャート DOM 幅から算出する可変値
const pxPerMinute = ref(6)     // 初期値はダミー
const gridStep    = computed(() => pxPerMinute.value * 10)   // 10 分

function recalcPxPerMinute () {
  // g-gantt-chart 全体の実幅
  const el = wrapperRef.value
  if (!el) return
  const totalMin = props.hoursPerChart * 60
  pxPerMinute.value = el.scrollWidth / totalMin
}

onMounted(() => {
  // 初回計算
  nextTick(recalcPxPerMinute)
  // 画面リサイズや時間帯変更でも再計算
  window.addEventListener('resize', recalcPxPerMinute)
})

watch([chartStart, chartEnd], () => nextTick(recalcPxPerMinute))


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
            background: statusColorHex(r.status)
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

  const attends = await getShiftPlans({
    date  : props.date,
    store : props.storeId || undefined
  })
  console.table(attends)

const shiftBars = attends.map(a => {
  // 行 ID → rows の id と必ず揃える
  const castId = a.cast_profile ?? a.cast_id;

  // a.start_at / end_at は "HH:MM:SS"
  const st = dayjs(`${a.date}T${a.start_at}`);
  const ed = dayjs(`${a.date}T${a.end_at}`);

  return {
    rowId : castId,
    from  : st.toDate(),
    to    : ed.toDate(),
    isShift : true,
    
    ganttBarConfig : {
      id   : `shift_${a.id}`,
      label: '',
      classes: ['shift-bar'],
      style: {
        background : SHIFT_COLOR,
        border     : 'none',
        // zIndex     : 0,
        pointerEvents: 'none',
      }
    }
  };
});



  bars.value = [...list, ...shiftBars]
 
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

/* ───────── emit ───────── */
const emit = defineEmits(['update','bar-click','request-new'])

function onDragEnd({ bar }) {
  emit('update', {
    reservationId: bar.reservationId,
    newStartISO  : dayjs(bar.from).toISOString()
  })
}

function onBarClick({ bar }) {
  emit('bar-click', { reservationId: bar.reservationId })
}

/* ───────── タイムラインクリックで予約 ───────── */
function onRowClick(e, castId) {
  if (e.target.closest('.g-gantt-bar')) return   // バー上は無視

  const rect    = wrapperRef.value.getBoundingClientRect()
  const x       = e.clientX - rect.left + wrapperRef.value.scrollLeft
  const mins    = x / pxPerMinute.value
  const snapped = Math.floor(mins / 10) * 10     // 10 分スナップ

  const startISO = dayjs(chartStart.value)
                    .add(snapped, 'minute')
                    .toISOString()

  emit('request-new', { castId, startISO })
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

  <ul class="list-inline mb-3">
    <li v-for="(m, key) in STATUS_META" :key="key" class="list-inline-item me-3">
      <span class="badge" :class="`bg-${m.badge}`">{{ m.long }}</span>
    </li>
  </ul>
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

          <span
            v-if="row.place"
            class="badge badge-tip bg-light text-dark"
            :data-addr="row.placeAddr"
          >
          {{ row.place }}
        </span>
      </span>
      </div>
    </div>

    <!-- チャート側（横だけスクロール） -->
<div class="chart-col" ref="wrapperRef" :style="{'--grid-step': gridStep + 'px'}">
      <div class="now-line" :style="{ left: nowX + 'px' }"></div>
      <!-- ★ g-gantt-chart はそのまま -->
      <g-gantt-chart
        :chart-start="chartStart"
        :chart-end="chartEnd"
        :row-height="rowHeight"
        :width="chartWidth"
        precision="hour"
        :precision-step="10" 
        bar-start="from"
        bar-end="to"
        push-on-overlap
        @dragend-bar="onDragEnd"
        @click-bar="onBarClick"
        :style="{ '--grid-step': gridStep + 'px' }"
      >
        <g-gantt-row
          v-for="row in rows"
          :key="row.id"
          :bars="bars.filter(b => b.rowId === row.id)"
          @click="e => onRowClick(e, row.id)"
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

/* グリッド線 */
:deep(.g-gantt-chart) {
  position: relative;          /* 擬似要素の基準 */
  background: transparent;     /* 元の背景は不要 */
}

:deep(.g-gantt-chart)::before {
  content: '';
  position: absolute;
  inset: 0;                    /* 全面に展開 */
  background-image: linear-gradient(
    to right,
    rgba(0,0,0,.1) 1px,
    transparent 1px
  );
  background-size: var(--grid-step) 100%;
  pointer-events: none;
  z-index: 0;                  /* バーより下、now-line より下 */
}

.chart-col{
    position: relative;
}
/* ② now-line はグリッドより前面へ */
.now-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: red;
  opacity: .5;
  pointer-events: none;
  z-index: 2;                   /* ← 重要：grid より大きく */
}

/* ③ g-gantt-chart を透過にしておくと一層安全 */
:deep(.g-gantt-chart) {
  background: transparent;
}

/* deep で g-gantt-row 本体を relative にしておく */
:deep(.g-gantt-row) { position: relative; }


/* ① 上段の日付セルだけ消す */
:deep(.g-upper-timeunit) {
  display: none;
}

/* ② 高さが 24px 分だけ詰まるので、チャート全体を下げる */
:deep(.g-gantt-chart) {
  margin-top: -40px;   /* ← 上段セルの高さに合わせて調整 */
}

.g-timeunits-container:first-of-type{
  display: none;
}
/* ヒットエリア */
.row-hitarea {
  position: absolute;
  inset: 0;
  cursor: pointer;
  background: transparent;
  /* 好みで hover 色を付けても良い */
}

:deep([id^="shift_"]) { z-index: 0 !important; }

</style>