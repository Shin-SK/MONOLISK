<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import { fetchBasicDiscountRules } from '@/api'

const props = defineProps({
  tables: { type: Array, default: () => [] },
  tableId: { type: [Number, null], default: null },

  // 人数（親→子参照）。実表示は男+女、同期は emit('update:pax')
  pax: { type: Number, default: 0 },

  courseOptions: { type: Array, default: () => [] },
  customerName: { type: String, default: '' },
  customerResults: { type: Array, default: () => [] },
  customerSearching: { type: Boolean, default: false },

  seatTypeOptions: {
    type: Array,
    default: () => ([
      { code:'main',    label:'メイン' },
      { code:'counter', label:'カウンター' },
      { code:'box',     label:'ボックス' },
    ])
  },
  seatType: { type: String, default: 'main' },

  /* SET（60分固定） */
  male:   { type: Number, default: 0 },
  female: { type: Number, default: 0 },
  night:  { type: Boolean, default: false },
  special:{ type: String,  default: 'none' },

  // PC/List と一致：開始/終了（ISO文字列）
  openedAt:    { type: String, default: '' },  // bill.opened_at
  expectedOut: { type: String, default: '' },  // bill.expected_out（無ければ式で暫定）

  // PC/List と一致：延長分（分）・セット回数
  extMinutes:  { type: Number, default: 0 },   // bill.ext_minutes
  setRounds:   { type: Number, default: 0 },   // bill.set_rounds
})

const emit = defineEmits([
  'update:seatType','update:tableId','update:pax',
  'chooseCourse','clearCustomer','searchCustomer','pickCustomer',
  'applySet','save'
])

/* ===== 席種・テーブル ===== */
const seatTypeRef  = ref(props.seatType || 'main')
watch(() => props.seatType, v => { seatTypeRef.value = v || 'main' })

const safeTables = computed(() =>
  Array.isArray(props.tables) ? props.tables.filter(t => t && t.id!=null) : []
)

const seatTypeOptionsAuto = computed(() => {
  const set = new Map()
  for (const t of safeTables.value) {
    const code = String(t?.seat_type || 'main')
    if (!set.has(code)) {
      set.set(code, {
        code,
        label: code==='main' ? 'メイン'
            : code==='counter' ? 'カウンター'
            : code==='box' ? 'ボックス'
            : code
      })
    }
  }
  const fromProps = (props.seatTypeOptions || []).filter(o => o?.code)
  return fromProps.length ? fromProps : Array.from(set.values())
})

function onSeatTypeInput (e){
  const v = e?.target?.value ?? 'main'
  emit('update:seatType', v)
}

const filteredTables = computed(() => {
  const code = seatTypeRef.value
  if (!safeTables.value.length) return []
  if (safeTables.value[0]?.seat_type == null) return safeTables.value
  return safeTables.value.filter(t => String(t.seat_type) === String(code))
})

/* ===== SET（男・女・深夜・特例） ===== */
const maleRef    = ref(props.male)
const femaleRef  = ref(props.female)
const nightRef   = ref(props.night)
const specialRef = ref(props.special)
watch(() => props.male,   v => maleRef.value   = v)
watch(() => props.female, v => femaleRef.value = v)

const totalGuests = computed(() =>
  (Number(maleRef.value)||0) + (Number(femaleRef.value)||0)
)

// 男/女変更時に親へ pax 同期（PCと整合）
watch([maleRef, femaleRef], () => {
  emit('update:pax', totalGuests.value)
}, { immediate: true })

const qtyOf = (k) => (k==='male' ? Number(maleRef.value)||0 : Number(femaleRef.value)||0)
function inc(k){ if (k==='male') maleRef.value = qtyOf('male')+1; else femaleRef.value = qtyOf('female')+1 }
function dec(k){ if (k==='male') maleRef.value = Math.max(0, qtyOf('male')-1); else femaleRef.value = Math.max(0, qtyOf('female')-1) }

/* ===== 割引ルール ===== */
const discountRules = ref([{ code: 'none', name: '通常' }])
onMounted(async () => {
  try {
    const list = await fetchBasicDiscountRules()
    const arr = (Array.isArray(list) ? list : [])
      .filter(r => r && r.code && r.name)
      .map(r => ({ code:String(r.code), name:String(r.name) }))
    discountRules.value = [{ code:'none', name:'通常' }, ...arr]
    if (!discountRules.value.some(r => r.code === specialRef.value)) specialRef.value = 'none'
  } catch {
    discountRules.value = [{ code:'none', name:'通常' }]
    specialRef.value = 'none'
  }
})

/* ===== 情報パネル（PC/List準拠） ===== */
// 伝票が立ったら（openedAt / pax>0 / tableId）出っぱなし
const infoShown = ref(false)
onMounted(() => {
  if (props.openedAt || totalGuests.value > 0 || props.tableId != null) infoShown.value = true
})
watch([() => props.openedAt, totalGuests, () => props.tableId], ([o, g, t]) => {
  if (!infoShown.value && (o || g > 0 || t != null)) infoShown.value = true
})

// 開始：唯一の真実は openedAt（“今”で埋めない）
const startISO = ref('')
watch(() => props.openedAt, v => { startISO.value = v || '' }, { immediate: true })

// 終了：expectedOut 優先。無ければ式：opened_at + (set_rounds×60 + ext_minutes) 分
const endISO   = ref('')
watch(() => props.expectedOut, v => { endISO.value = v || '' }, { immediate: true })

const computedEndISO = computed(() => {
  if (endISO.value) return endISO.value
  if (!startISO.value) return '' // opened_at 無しなら計算もしない
  const addMin = (Number(props.setRounds)||0) * 60 + (Number(props.extMinutes)||0)
  if (addMin <= 0) return ''
  return dayjs(startISO.value).add(addMin, 'minute').toISOString()
})

// 表示（HH:mm）と編集用（datetime-local）の両方を持つ
const startDisplay = computed(() => startISO.value ? dayjs(startISO.value).format('HH:mm') : '-')
const endDisplay   = computed(() => {
  const iso = endISO.value || computedEndISO.value
  return iso ? dayjs(iso).format('HH:mm') : '-'
})
// 編集用のローカル値（datetime-local にそのまま入れる）
const startLocal = ref('')
const endLocal   = ref('')
// props → 編集用初期化
watch(startISO, v => { startLocal.value = v ? dayjs(v).format('YYYY-MM-DDTHH:mm') : '' }, { immediate:true })
watch(endISO,   v => { endLocal.value   = v ? dayjs(v).format('YYYY-MM-DDTHH:mm')   : '' }, { immediate:true })

// 編集（今回は表示主体。必要になれば emit で親へ反映）
const editingHeader = ref(false)
function beginEditHeader(){
  // openedAt が無い既存ドラフトでも、編集欄は空で開始（“今”は入れない）
  editingHeader.value = true
}
function cancelEditHeader(){
  // 編集前のISOに戻す
  startLocal.value = startISO.value ? dayjs(startISO.value).format('YYYY-MM-DDTHH:mm') : ''
  endLocal.value   = endISO.value   ? dayjs(endISO.value).format('YYYY-MM-DDTHH:mm')   : ''
  editingHeader.value = false
}
function confirmEditHeader(){
  // ローカル入力 → ISO に変換して親へ通知。空は null 扱い
  const opened_at    = startLocal.value ? dayjs(startLocal.value).toISOString() : null
  const expected_out = endLocal.value   ? dayjs(endLocal.value).toISOString()   : null
  // 楽観更新（このパネルの表示も即更新）
  startISO.value = opened_at || ''
  endISO.value   = expected_out || ''
  editingHeader.value = false
  // 親（モーダル）に patch させる
  emit('update-times', { opened_at, expected_out })
}

// テーブル番号 / 人数 / 延長数（PC/List の式：ext_minutes/30）
const tableNumberLabel = computed(() => {
  const id = props.tableId
  const hit = safeTables.value.find(t => Number(t.id)===Number(id))
  return hit?.number ?? (id ?? '-')
})
// 人数ラベル：最優先は男+女、両方0のときだけ props.pax を表示に利用
const paxLabel = computed(() => {
  const g = totalGuests.value
  return g > 0 ? g : (Number(props.pax)||0)
})
const extCountView = computed(() => {
  const m = Number(props.extMinutes)||0
  return m ? Math.floor(m / 30) : 0
})

/* 追加（黄色ボタン） */
function applySet(){
  const m = Number(maleRef.value||0), f = Number(femaleRef.value||0)
  if (m+f <= 0) { alert('SETの人数を入力してください'); return }

  emit('applySet', {
    lines: [
      { type:'set',   code:'setMale',   qty:m },
      { type:'set',   code:'setFemale', qty:f },
      ...(nightRef.value ? [{ type:'addon', code:'addonNight', qty:(m+f) }] : []),
    ],
    config: { night: !!nightRef.value },
    discount_code: (specialRef.value !== 'none') ? String(specialRef.value) : null,
  })
}

const q = ref('')
const doSearch = () => emit('searchCustomer', q.value.trim())
</script>

<template>
  <div class="panel base">
    <div class="wrap d-flex flex-column gap-3 w-100">

      <!-- 情報パネル（PC/List準拠：出っぱなし） -->
      <div v-if="infoShown" class="box border border-secondary rounded p-3">
        <div class="d-flex flex-column gap-2 align-items-center justify-content-between">
          <!-- 表示モード -->
          <template v-if="!editingHeader">
            <div class="d-flex align-items-center gap-2">
              <span class="fs-1 fw-bold">
                {{ startDisplay }} – {{ endDisplay }}
              </span>
              <button type="button" class="btn btn-link p-0" @click="beginEditHeader" title="編集">
                <IconPencil :size="20" />
              </button>
            </div>
          </template>

          <!-- 編集モード（双方向バインドで編集可能） -->
          <template v-else>
            <div class="df-center flex-column gap-3 w-100">
              <div class="d-flex flex-column gap-3 align-items-center w-100">
                <div class="wrap w-100">
                  <span>開始時間</span>
                  <input type="datetime-local" class="form-control form-control-sm w-100" v-model="startLocal" />
                </div>
                <div class="wrap w-100">
                  <span>終了時間</span>
                  <input type="datetime-local" class="form-control form-control-sm w-100" v-model="endLocal" />
                </div>
              </div>
              <div class="wrap d-flex align-items-center gap-3 w-100">
                <button class="btn btn-success py-1 px-2 df-center gap-1 w-100" @click="confirmEditHeader" title="完了">
                  <IconCircleDashedCheck /><span>修正</span>
                </button>
                <button class="btn btn-danger py-1 px-2 df-center gap-1 w-100" @click="cancelEditHeader" title="取り消し">
                  <IconCircleDashedX /><span>取消</span>
                </button>
              </div>

            </div>
          </template>

          <div class="d-flex gap-3 align-items-end fs-5 fw-bold">
            <div class="d-flex align-items-center gap-1">
              <IconPinned/> {{ tableNumberLabel }}
            </div>
            <div class="d-flex align-items-center gap-1">
              <IconUsers /> {{ paxLabel }}
            </div>
            <div class="d-flex align-items-center gap-2">
              <IconRefresh />
              <span>{{ extCountView }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 席種 -->
      <div class="box">
        <div class="title"><IconCategory2 /> 席種</div>
        <div class="btn-group w-100">
          <template v-for="opt in seatTypeOptionsAuto" :key="opt.code">
            <input type="radio" class="btn-check" :id="`st-${opt.code}`"
                   :value="opt.code" :checked="opt.code===seatTypeRef"
                   @change="onSeatTypeInput" />
            <label class="btn btn-outline-secondary btn-sm" :for="`st-${opt.code}`">{{ opt.label }}</label>
          </template>
        </div>
      </div>

      <!-- テーブル -->
      <div class="box">
        <div class="title"><IconPinned /> テーブル</div>
        <select class="form-select"
                :value="tableId"
                @change="e => $emit('update:tableId', e.target.value ? Number(e.target.value) : null)">
          <option :value="null">-</option>
          <option v-for="t in filteredTables" :key="t.id" :value="t.id">{{ t.number }}</option>
        </select>
      </div>

      <!-- SET（男・女・深夜・特例） -->
      <div class="box">
        <div class="title"><IconSettings2 /> セット</div>

        <div class="mb-3">
          <div class="d-flex align-items-center justify-content-between gap-3">
            <!-- 男性 -->
            <div class="d-flex align-items-center">
              <IconGenderMale class="text-info" stroke-width="1.5"/>
              <div class="cartbutton d-flex align-items-center">
                <div class="d-flex align-items-center gap-3 bg-light h-auto p-2 m-2" style="border-radius:100px;">
                  <button type="button" @click="dec('male')" :class="{ invisible: qtyOf('male')===0 }">
                    <IconMinus :size="16" />
                  </button>
                  <span>{{ qtyOf('male') }}</span>
                  <button type="button" @click="inc('male')"><IconPlus :size="16" /></button>
                </div>
              </div>
            </div>
            <!-- 女性 -->
            <div class="d-flex align-items-center">
              <IconGenderFemale class="text-danger" stroke-width="1.5"/>
              <div class="cartbutton d-flex align-items-center">
                <div class="d-flex align-items-center gap-3 bg-light h-auto p-2 m-2" style="border-radius:100px;">
                  <button type="button" @click="dec('female')" :class="{ invisible: qtyOf('female')===0 }">
                    <IconMinus :size="16" />
                  </button>
                  <span>{{ qtyOf('female') }}</span>
                  <button type="button" @click="inc('female')"><IconPlus :size="16" /></button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 追加項目 -->
        <div class="mb-2">
          <div class="title">追加項目</div>
          <div class="d-flex flex-column gap-3">
            <div class="wrap d-flex align-items-center gap-2">
              <label class="form-check-label btn btn-sm btn-outline-secondary me-2" for="night">深夜料金(+1,000/人)</label>
              <div class="form-check form-switch d-flex align-items-center gap-3">
                <input class="form-check-input" type="checkbox" id="night" v-model="nightRef">
              </div>
            </div>

            <div class="btn-group flex-wrap gap-2" role="group" aria-label="特例">
              <template v-for="r in discountRules" :key="r.code">
                <input class="btn-check" type="radio" name="sp" :id="`sp-${r.code}`"
                       :value="r.code" v-model="specialRef">
                <label class="btn btn-sm"
                       :class="specialRef===r.code ? 'btn-secondary' : 'btn-outline-secondary'"
                       :for="`sp-${r.code}`">
                  {{ r.name }}
                </label>
              </template>
            </div>
          </div>
        </div>

        <button class="btn btn-warning w-100 my-5" @click="applySet">この内容を追加</button>
      </div>

      <!-- 顧客 -->
      <div class="box">
        <div class="title"><IconUserScan /> 顧客</div>
        <div class="form-control bg-light position-relative">
          {{ customerName || '未選択' }}
          <button class="position-absolute top-0 bottom-0 end-0" :disabled="!customerName" @click="$emit('clearCustomer')"><IconX :size="16"/></button>
        </div>
        <div class="mt-2 position-relative">
          <input class="form-control" type="text" v-model="q" placeholder="名前／TEL などで検索" @keyup.enter="doSearch">
          <button class="position-absolute top-0 bottom-0 end-0" @click="doSearch"><IconSearch :size="16" /></button>
        </div>
        <div v-if="customerSearching" class="small text-muted mt-2">検索中…</div>
        <ul v-if="customerResults && customerResults.length" class="mt-2 ps-0" style="list-style:none;">
          <li v-for="(c,i) in customerResults" :key="c?.id ?? i" class="d-flex align-items-center gap-2 py-2 border-top">
            <div class="flex-grow-1">
              <div class="fw-bold">{{ c.alias || c.full_name || ('#'+c.id) }}</div>
              <div class="small text-muted">{{ c.phone || c.email || '' }}</div>
            </div>
            <button class="btn btn-sm btn-primary" @click="$emit('pickCustomer', c)">選択</button>
          </li>
        </ul>
        <div v-else-if="q" class="small text-muted mt-2">検索結果なし</div>
      </div>

      <div class="savebutton">
        <button class="btn btn-primary w-100 mt-4" @click="$emit('save')">保存</button>
      </div>
    </div>
  </div>
</template>