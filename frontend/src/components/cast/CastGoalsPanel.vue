<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import dayjs from 'dayjs'
import { listCastGoals, createCastGoal, deleteCastGoal } from '@/api'


// 親から me を受け取り: { cast_id, ... } 想定（/api/me）
const props = defineProps({
  castId: { type: [Number, String], required: false }, 
  me: { type: Object, required: false, default: () => ({}) },
})

// 状態
const loading = ref(false)
const saving  = ref(false)
const goals   = ref([])            // サーバ側のゴール一覧
const progressMap = ref({})        // goalId -> { value, percent, milestones:{50,80,90,100} }

const showForm = ref(false)

const resetForm = () => {
  form.value = {
    metric: 'sales_amount',
    target_value: 50000,
    period_from: dayjs().startOf('month').format('YYYY-MM-DD'),
    period_to  : dayjs().endOf('month').format('YYYY-MM-DD'),
  }
}

const isValid = computed(() => {
  const t = Number(form.value.target_value) || 0
  const f = form.value.period_from
  const to = form.value.period_to
  return t > 0 && f && to && dayjs(f).isSameOrBefore(dayjs(to))
})

// 安全に数値化 & フォールバック
const resolvedCastId = computed(() => {
  const direct = props.castId != null ? Number(props.castId) : NaN
  if (Number.isFinite(direct)) return direct
  const fromMe = props.me?.cast_id != null ? Number(props.me.cast_id) : NaN
  return Number.isFinite(fromMe) ? fromMe : null
})

// 以降は resolvedCastId.value を必ず使う
function assertCid() {
  if (!resolvedCastId.value) throw new Error('castId not resolved')
}

// サーバ側の正規コードに合わせる（暫定マッピング）
const METRIC_ALIAS_TO_SERVER = {
  sales_amount:        'revenue',
  nominations_count:   'nominations',
  inhouse_count:       'inhouse',
  champagne_revenue:   'champ_revenue',
  champagne_bottles:   'champ_count',
};

// 作成フォーム
const form = ref({
  metric: 'sales_amount',
  target_value: 50000,
  period_from: dayjs().startOf('month').format('YYYY-MM-DD'),
  period_to  : dayjs().endOf('month').format('YYYY-MM-DD'),
})

const metricOptions = [
  { value:'sales_amount',        label:'売上金額(¥)' },
  { value:'nominations_count',   label:'本指名 本数' },
  { value:'inhouse_count',       label:'場内指名 本数' },
  { value:'champagne_revenue',   label:'シャンパン売上(¥)' },
  { value:'champagne_bottles',   label:'シャンパン本数' },
]

function fmtYen(n){ return '¥' + (Number(n)||0).toLocaleString() }

// 進捗計算のメイン（できるだけ既存エンドポイントで集計）
async function computeProgressForGoal(g){
  const castId = resolvedCastId.value
  if (!castId) return { value:0, percent:0, milestones:{50:false,80:false,90:false,100:false} }

  // 期間
  const df = g.start_date || g.period_from
  const dt = g.end_date   || g.period_to

  // データ取得（必要十分な粒度）
  // /billing/cast-items/?cast=...&date_from=...&date_to=...
  const items = await fetchCastItemDetails(castId, { date_from: df, date_to: dt, limit: 2000 })
    .catch(() => [])

  let val = 0
  const wantCats = new Set(['champagne','original-champagne'])

  for (const it of (Array.isArray(items) ? items : [])) {
    const qty   = Number(it.qty || 0)
    const money = Number(it.subtotal || 0)
    const cat   = (it.category && (it.category.code || it.category)) || null
    const isNom = it.is_nomination === true
    const isIn  = it.is_inhouse    === true

    switch (g.metric) {
      case 'sales_amount':
        val += money
        break
      case 'nominations_count':
        // 指名本数： is_nomination の数量合計
        val += isNom ? qty : 0
        break
      case 'inhouse_count':
        // 場内指名本数： is_inhouse の数量合計
        val += isIn ? qty : 0
        break
      case 'champagne_revenue':
        if (cat && wantCats.has(cat)) val += money
        break
      case 'champagne_bottles':
        if (cat && wantCats.has(cat)) val += qty
        break
    }
  }

  const target = Number(g.target_value || 0) || 0
  const pct = target > 0 ? Math.min(100, Math.floor((val / target) * 100)) : (val > 0 ? 100 : 0)
  return {
    value: val,
    percent: pct,
    milestones: {
      50 : pct >= 50,
      80 : pct >= 80,
      90 : pct >= 90,
      100: pct >= 100,
    }
  }
}

async function refresh(){
  loading.value = true
  try{
    const castId = resolvedCastId.value
    if (!castId) { goals.value = []; progressMap.value = {}; return }
    const list = await listCastGoals(castId)
    goals.value = Array.isArray(list) ? list.slice(0, 50) : []

    // サーバが返す進捗をそのまま使う
    const map = {}
    for (const g of goals.value) {
      map[g.id] = {
        value:   g.progress_value ?? 0,
        percent: g.progress_percent ?? 0,
        milestones: {
          50 : (g.hits || []).includes(50),
          80 : (g.hits || []).includes(80),
          90 : (g.hits || []).includes(90),
          100: (g.hits || []).includes(100),
        }
      }
    }
    progressMap.value = map
  } finally {
    loading.value = false
  }
}

async function addGoal(){
  if (saving.value) return
  saving.value = true
  try{
	assertCid()
  const castId = resolvedCastId.value
  const created = await createCastGoal(castId, {
    cast: castId,
    metric: METRIC_ALIAS_TO_SERVER[form.value.metric] ?? form.value.metric,
    target_value: Number(form.value.target_value) || 0,
    period_kind: 'custom',
    start_date: form.value.period_from,
    end_date  : form.value.period_to,
  })
  // 即時に一番下へ
  goals.value.push(created)
  resetForm()
  showForm.value = false
  await nextTick()
  document.getElementById(`goal-${created.id}`)?.scrollIntoView({ behavior:'smooth', block:'center' })
  // 進捗はレスポンスの read-only を使う
  progressMap.value[created.id] = {
    value:   created.progress_value ?? 0,
    percent: created.progress_percent ?? 0,
    milestones: {
      50:  (created.hits || []).includes(50),
      80:  (created.hits || []).includes(80),
      90:  (created.hits || []).includes(90),
      100: (created.hits || []).includes(100),
    },
  }
  }catch(e){
    console.error('createCastGoal failed:', e?.response?.status, e?.response?.data || e)
    alert('作成に失敗: ' + JSON.stringify(e?.response?.data || e?.message))
  }finally{
    saving.value = false
  }
}

async function removeGoal(g){
  if (!confirm('この目標を削除しますか？')) return
  const castId = resolvedCastId.value
  await deleteCastGoal(castId, g.id).catch(()=>{})
  goals.value = goals.value.filter(x => x.id !== g.id)
  delete progressMap.value[g.id]
}

onMounted(() => { if (resolvedCastId.value) refresh() })
watch(resolvedCastId, (v, ov) => { if (v && v !== ov) refresh() })

// 表示名＆アイコンの対応（サーバ正規コードに合わせている）
const DISPLAY_META = {
  revenue:        { name: '売上金額',       unit: '円',  icon: 'IconCurrencyYen' },
  nominations:    { name: '本指名 本数',     unit: '本',  icon: 'IconUserStar'   },
  inhouse:        { name: '場内指名 本数',   unit: '本',  icon: 'IconDoorEnter'  },
  champ_revenue:  { name: 'シャンパン売上',   unit: '円',  icon: 'IconBottle'     },
  champ_count:    { name: 'シャンパン本数',   unit: '本',  icon: 'IconBottle'     },
}

// ★ メトリック別の“表示用オブジェクト”を返す
function goalView(g){
  // g.metric はサーバ側の正規コード（revenue / nominations / ...）
  const meta  = DISPLAY_META[g.metric] || { name: g.metric, unit: '', icon: 'IconTargetArrow' }
  const money = (meta.unit === '円')

  const s = g.start_date || g.period_from
  const e = g.end_date   || g.period_to

  const curVal = progressMap.value[g.id]?.value ?? 0
  const pct    = progressMap.value[g.id]?.percent ?? 0
  const hits   = progressMap.value[g.id]?.milestones || {} // {50:true,...}

  const fmtTarget = money ? fmtYen(g.target_value) : `${g.target_value} ${meta.unit || ''}`.trim()
  const fmtCurrent= money ? fmtYen(curVal)         : `${curVal} ${meta.unit || ''}`.trim()

  return {
    // タイトル部
    label: meta.name,
    icon : meta.icon,                       // <component :is="...">
    // 期間
    from : dayjs(s).format('YYYY/M/D'),
    to   : dayjs(e).format('YYYY/M/D'),
    // 値
    targetPretty  : fmtTarget,
    currentPretty : fmtCurrent,
    percent       : pct,
    hits,                                     // {50:true,80:true,...}
  }
}


</script>

<template>
  <div class="pb-5">

    <div class="wrap position-relative mb-5">
      <div class="position-absolute top-0 end-0">
        <button
          type="button"
          class="btn btn-sm"
          @click="refresh"
        >
          <IconRefresh />
        </button>
      </div>
      <h2 class="fs-5 df-center gap-1"><IconTargetArrow />目標一覧</h2>
      <div v-if="loading">読み込み中…</div>
      <div v-else-if="!goals.length">目標はまだありません</div>
      <ul v-else class="list-unstyled">
      
        <li v-for="g in goals" :key="g.id" :id="`goal-${g.id}`" class="mb-3">
          <div class="card shadow-sm border-0">
            <div class="card-header">
              <div class="d-flex align-items-center gap-2 justify-content-between">
                <div class="wrap d-flex align-items-center">
                  <IconCalendar class="me-1"/>
                  <div class="span">
                    <span class="">{{ goalView(g).from }}</span>
                    <span> 〜 </span>
                    <span class="">{{ goalView(g).to }}</span>
                  </div>
                </div>
                <button type="button" class="text-danger" @click="removeGoal(g)">
                  <IconX class="" />
                </button>
              </div>
            </div>
            <div class="card-body position-relative">
              <!-- 期間・目標・現在値 -->
              <div class="d-flex gap-3 align-items-center mt-2">
                <div class="badge bg-dark text-light">
                  {{ goalView(g).label }}
                </div>
                <div class="d-flex align-items-center gap-1">
                  <span class="fs-3 fw-bold lh-1">{{ goalView(g).currentPretty }}</span>
                  <span class="lh-1">/</span>
                  <span class="small text-muted lh-1">{{ goalView(g).targetPretty }}</span>
                </div>
              </div>
              <!-- 進捗バー -->
              <div class="progress mt-2" style="height:10px;">
                <div
                  class="progress-bar"
                  role="progressbar"
                  :style="{ width: goalView(g).percent + '%' }"
                  :aria-valuenow="goalView(g).percent" aria-valuemin="0" aria-valuemax="100">
                </div>
              </div>
              <div class="mt-1 small text-end text-muted">
                {{ goalView(g).percent }}%
              </div>
              <!-- マイルストーン -->
              <!-- <div class="d-flex gap-2 mt-2">
                <span class="badge" :class="goalView(g).hits[50]  ? 'bg-success' : 'bg-light text-muted'">50%</span>
                <span class="badge" :class="goalView(g).hits[80]  ? 'bg-success' : 'bg-light text-muted'">80%</span>
                <span class="badge" :class="goalView(g).hits[90]  ? 'bg-success' : 'bg-light text-muted'">90%</span>
                <span class="badge" :class="goalView(g).hits[100] ? 'bg-success' : 'bg-light text-muted'">100%</span>
              </div> -->
            </div>
          </div>
        </li>
      </ul>
    </div>

    <div class="wrap">
      <h3 class="fw-bold df-center gap-1 fs-5 mb-2"><IconTargetArrow />目標を設定</h3>
      <small class="df-center">目標をクリアできるようサポートします！</small>
      <!-- 作成フォーム -->
      <div class="form-area mt-3">
        <div class="card border-0 shadow-sm mb-5">
          <div class="card-body">
            <!-- 指標 & 目標値 -->
            <div class="row g-3 align-items-center">
              <div class="col-2">
                <label class="form-label">指標</label>
              </div>
              <div class="col-10">
                <select v-model="form.metric" class="form-select">
                  <option v-for="opt in metricOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
              <div class="col-2">
                <label class="form-label">目標</label>
              </div>
              <div class="col-10">
                <input
                  type="number"
                  min="0"
                  v-model.number="form.target_value"
                  class="form-control"
                  placeholder="例）50000"
                />
              </div>
              <div class="col-2 d-flex">
                <div class="form-label">期間</div>
              </div>
              <div class="col-10">
                <d class="wrap">
                  <input type="date" class="form-control mb-3" placeholder="いつから" v-model="form.period_from" />
                  <input type="date" class="form-control" placeholder="いつまで" v-model="form.period_to" />
                </d iv>
              </div>
              <div class="col-6">
                <button
                  type="button"
                  class="btn btn-sm btn-primary w-100 df-center"
                  :disabled="saving || !isValid"
                  @click="addGoal"
                  title="追加"
                >
                  <IconPlus class="me-1" /> 追加
                </button>
              </div>
              <div class="col-6">
                <button
                  type="button"
                  class="btn btn-sm btn-outline-secondary w-100"
                  @click="resetForm"
                  title="クリア"
                >
                  クリア
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>


  </div>
</template>
