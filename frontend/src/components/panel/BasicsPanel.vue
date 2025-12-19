<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import Avatar from '@/components/Avatar.vue'
import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'
import { fetchBasicDiscountRules, fetchDiscountRules, fetchStoreSeatSettings, fetchMasters } from '@/api'  // ← 追加

const props = defineProps({
  tables: { type: Array, default: () => [] },
  tableId: { type: [Number, null], default: null },

  currentCasts: { type: Array, default: () => [] },  // 現在着席中のキャスト

  historyEvents: {
    type: Array,
    default: () => [] 
  },

  // 人数（親→子参照）。実表示は男+女、同期は emit('update:pax')
  pax: { type: Number, default: 0 },

  courseOptions: { type: Array, default: () => [] },
  customerName: { type: String, default: '' },
  customerResults: { type: Array, default: () => [] },
  customerSearching: { type: Boolean, default: false },
  customer: { type: Object, default: null },  // 選択中の顧客情報

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

  // 小計
  subtotal: { type: Number, default: 0 },   // bill.subtotal
})

const emit = defineEmits([
  'update:seatType','update:tableId','update:pax',
  'chooseCourse','clearCustomer','searchCustomer','pickCustomer',
  'applySet','save','switchPanel','update-times'
])

/* ===== 席種・テーブル ===== */
const seatTypeRef  = ref(props.seatType || 'main')
watch(() => props.seatType, v => { seatTypeRef.value = v || 'main' })

const safeTables = computed(() =>
  Array.isArray(props.tables) ? props.tables.filter(t => t && t.id!=null) : []
)

// 自店舗の "使える席種" 候補を API で取得（StoreSeatSetting 起点）
const storeSeatSettings = ref([])    // ← 追加
// code -> id のマップ（StoreSeatSetting に seat_type が載ってる）
const seatTypeIdByCode = computed(() => {
  const m = new Map()
  for (const s of storeSeatSettings.value || []) {
    const code = String(s.seat_type_code || '')
    const id   = Number(s.seat_type)
    if (code && Number.isFinite(id)) m.set(code, id)
  }
  return m
})

onMounted(async () => {
  try {
    storeSeatSettings.value = await fetchStoreSeatSettings()
    // 初期 seatType が候補に無ければ、先頭に合わせる
    const codes = new Set((storeSeatSettings.value||[]).map(s => s.seat_type_code))
    if (!codes.has(String(seatTypeRef.value)) && codes.size) {
      seatTypeRef.value = Array.from(codes)[0]
      emit('update:seatType', seatTypeRef.value)
    }
  } catch (e) { console.warn('[BasicsPanel] load seat settings failed', e) }
})

// UI表示用の席種ボタン（コード＋表示名）
const seatTypeOptionsAuto = computed(() => {
  const list = storeSeatSettings.value || []
  if (list.length) {
    const seen = new Map()
    for (const s of list) {
      const code = String(s.seat_type_code || '')
      if (!code) continue
      if (!seen.has(code)) seen.set(code, { code, label: s.seat_type_display || code })
    }
    return Array.from(seen.values())
  }
  // フォールバック：渡ってきた tables から自動推定（初期表示用）
  const set = new Map()
  for (const t of safeTables.value) {
    const code = String(t?.seat_type_code ?? t?.seat_type ?? '')
    if (!code) continue
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
  return Array.from(set.values())
})

// 卓の絞り込みは seat_type（id）で
const filteredTables = computed(() => {
  const code = String(seatTypeRef.value || '')
  if (!code) return safeTables.value
  // ① code で合うテーブル（サーバが seat_type_code を返せる場合）
  const byCode = safeTables.value.filter(t => String(t?.seat_type_code ?? '') === code)
  if (byCode.length) return byCode
  // ② 保険：code -> id に変換して id で絞る（古いレスポンスでも動く）
  const id = seatTypeIdByCode.value.get(code)
  if (id != null) return safeTables.value.filter(t => Number(t?.seat_type) === id)
  // ③ 何も合わなければ全件（UX保険）
  return safeTables.value
})

function onSeatTypeInput (e){
  const v = e?.target?.value ?? 'main'
  emit('update:seatType', v)
}


/* ===== SET（男・女・深夜・特例） ===== */
const maleRef    = ref(props.male)
const femaleRef  = ref(props.female)
const nightRef   = ref(props.night)
const specialRef = ref(props.special)
const selectedSet = ref('')  // 選択したSET商品ID
const setQtyMap = ref({})    // セット商品ごとの数量 { masterId: qty }
watch(() => props.male,   v => maleRef.value   = v)
watch(() => props.female, v => femaleRef.value = v)

// 再オープン時に男女が0でも pax が残っていれば復元する
watch(() => props.pax, v => {
  const currentTotal = (Number(maleRef.value)||0) + (Number(femaleRef.value)||0)
  const newTotal = Number(v)||0
  if (currentTotal === 0 && newTotal > 0) {
    maleRef.value = newTotal
    femaleRef.value = 0
  }
})

const totalGuests = computed(() =>
  (Number(maleRef.value)||0) + (Number(femaleRef.value)||0)
)

// 男/女変更時に親へ pax 同期（男+女が0なら上書きしない）
watch([maleRef, femaleRef], ([m, f]) => {
  const total = (Number(m) || 0) + (Number(f) || 0)
  if (total === 0) return
  emit('update:pax', total)
}, { immediate: true })

const qtyOf = (k) => (k==='male' ? Number(maleRef.value)||0 : Number(femaleRef.value)||0)
function inc(k, id){ 
  if (k==='male') maleRef.value = qtyOf('male')+1
  else if (k==='female') femaleRef.value = qtyOf('female')+1
  else if (k==='set') {
    setQtyMap.value[id] = (Number(setQtyMap.value[id])||0) + 1
  }
}
function dec(k, id){ 
  if (k==='male') maleRef.value = Math.max(0, qtyOf('male')-1)
  else if (k==='female') femaleRef.value = Math.max(0, qtyOf('female')-1)
  else if (k==='set') {
    setQtyMap.value[id] = Math.max(0, (Number(setQtyMap.value[id])||0) - 1)
  }
}

/* ===== SET商品マスタ（setMale/setFemale含む） ===== */
const setMasters = ref({})
onMounted(async () => {
  try {
    const list = await fetchMasters()
    // 後方互換: legacy カテゴリ 'setMale' / 'setFemale' も拾う。show_in_menu は内部操作なので無視。
    const sets = (list || []).filter(m => {
      const cat = String(m?.category?.code || '')
      if (cat.startsWith('set')) return true  // 'set','setMale','setFemale'
      return false
    })
    // IDキーのマップ（選択 UI 用）。価格昇順で見やすく。
    const sorted = sets.slice().sort((a,b) => (Number(a.price_regular)||0) - (Number(b.price_regular)||0))
    setMasters.value = Object.fromEntries(sorted.map(m => [String(m.id), m]))
  } catch (e) {
    console.warn('[BasicsPanel] fetchMasters failed:', e?.message)
  }
})

/* ===== 割引ルール（店舗×Basic用だけ出す） ===== */
const discountRules = ref([{ code: 'none', name: '通常' }])
const hydrated = ref(false)

onMounted(async () => {
  try {
    const list = await fetchDiscountRules({ is_active: true, place: 'basics' })
    const arr = (Array.isArray(list) ? list : [])
      .filter(r => r && r.code && r.name)
      .map(r => ({ code: String(r.code), name: String(r.name) }))
    discountRules.value = [{ code: 'none', name: '通常' }, ...arr]
    if (!discountRules.value.some(r => r.code === specialRef.value)) {
      specialRef.value = 'none'
    }
  } catch {
    discountRules.value = [{ code: 'none', name: '通常' }]
    specialRef.value = 'none'
  }
  hydrated.value = true
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

// 現在着席中のキャスト
const safeCurrent = computed(() =>
  Array.isArray(props.currentCasts) ? props.currentCasts.filter(c => c && c.id != null) : []
)

const miniTab = ref('customer')

// ナビゲーションタブの状態管理
// 既存伝票（openedAt有り）の場合はinfoタブ、新規の場合はfirstタブ
const activeTab = ref('first')  // 'first', 'info', 'customer'

// 伝票が既に立ち上がっている場合はinfoタブをデフォルト表示
watch(() => props.openedAt, (val) => {
  if (val && activeTab.value === 'first') {
    activeTab.value = 'info'
  }
}, { immediate: true })

// タブ切り替え（表示/非表示）
function switchTab(tabId) {
  activeTab.value = tabId
}

// info パネル編集状態管理
const editingStart = ref(false)
const editingEnd = ref(false)
const editingTable = ref(false)
const editingPax = ref(false)
const editingCustomer = ref(false)

// 編集用ローカル値
const editStartLocal = ref('')
const editEndLocal = ref('')
const editTableLocal = ref(null)
const editPaxLocal = ref(0)
const customerQuery = ref('')

// 開始時刻編集
function beginEditStart() {
  editStartLocal.value = startISO.value ? dayjs(startISO.value).format('YYYY-MM-DDTHH:mm') : ''
  editingStart.value = true
}
function saveEditStart() {
  const opened_at = editStartLocal.value ? dayjs(editStartLocal.value).toISOString() : null
  startISO.value = opened_at || ''
  emit('update-times', { opened_at, expected_out: endISO.value || null })
  editingStart.value = false
}

// 終了時刻編集
function beginEditEnd() {
  editEndLocal.value = endISO.value ? dayjs(endISO.value).format('YYYY-MM-DDTHH:mm') : ''
  editingEnd.value = true
}
function saveEditEnd() {
  const expected_out = editEndLocal.value ? dayjs(editEndLocal.value).toISOString() : null
  endISO.value = expected_out || ''
  emit('update-times', { opened_at: startISO.value || null, expected_out })
  editingEnd.value = false
}

// テーブル編集
function beginEditTable() {
  editTableLocal.value = props.tableId
  editingTable.value = true
}
function saveEditTable() {
  emit('update:tableId', editTableLocal.value)
  editingTable.value = false
}

// 人数編集
function beginEditPax() {
  editPaxLocal.value = Number(props.pax) || 0
  editingPax.value = true
}
function saveEditPax() {
  emit('update:pax', Number(editPaxLocal.value) || 0)
  editingPax.value = false
}

// 延長→会計パネルへ
function goToPayPanel() {
  emit('switchPanel', 'pay')
}

// 顧客編集（Multipul検索）
function beginEditCustomer() {
  switchTab('customer')
}
function searchCustomerInline() {
  if (customerQuery.value.trim()) {
    emit('searchCustomer', customerQuery.value.trim())
  }
}
function selectCustomerInline(c) {
  emit('pickCustomer', c)
  editingCustomer.value = false
}
function goToCustomerTab() {
  switchTab('customer')
  editingCustomer.value = false
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

// 小計フォーマット表示（¥12,345形式）
const subtotalFormatted = computed(() => {
  const amount = Number(props.subtotal) || 0
  return '¥' + amount.toLocaleString('ja-JP')
})

// 顧客情報表示用
const customerDisplayName = computed(() => {
  if (selectedCustomer.value) return selectedCustomer.value.alias || selectedCustomer.value.full_name || `#${selectedCustomer.value.id}`
  if (!props.customer) return 'ご新規様'
  return props.customer.alias || props.customer.full_name || `#${props.customer.id}`
})

const customerFullName = computed(() => {
  if (selectedCustomer.value) return selectedCustomer.value.full_name || '-'
  if (!props.customer) return '-'
  return props.customer.full_name || '-'
})

const customerBirthday = computed(() => {
  const c = selectedCustomer.value || props.customer
  if (!c?.birthday) return '-'
  return dayjs(c.birthday).format('YYYY年MM月DD日')
})

const customerLastOrder = computed(() => {
  const c = selectedCustomer.value || props.customer
  if (!c?.last_order) return '-'
  return c.last_order
})

const customerLastVisit = computed(() => {
  const c = selectedCustomer.value || props.customer
  if (!c?.last_visit_at) return '-'
  return dayjs(c.last_visit_at).format('YYYY/MM/DD HH:mm')
})

const customerLastCast = computed(() => {
  const c = selectedCustomer.value || props.customer
  if (!c?.last_cast_name) return '-'
  return c.last_cast_name
})

const customerMemo = computed(() => {
  const c = selectedCustomer.value || props.customer
  if (!c?.memo) return 'メモなし'
  return c.memo
})

/* 追加（黄色ボタン） */
function applySet(){
  const m = Number(maleRef.value||0), f = Number(femaleRef.value||0)
  const total = m + f
  if (total <= 0) { alert('人数を入力してください'); return }
  
  // setQtyMap から数量が1以上のセット商品を取得
  const selectedSets = Object.entries(setQtyMap.value)
    .filter(([id, qty]) => Number(qty) > 0)
    .map(([id, qty]) => ({ id: String(id), qty: Number(qty) }))
  
  if (selectedSets.length === 0) { alert('セット商品を選択してください'); return }
  
  // 最初のセット商品を使用（複数選択の場合は最初のもの）
  const firstSet = selectedSets[0]
  const selectedMaster = setMasters.value[firstSet.id]
  if (!selectedMaster) { alert('セット商品情報が取得できません'); return }

  // ★ セット追加時は opened_at（伝票の開始時刻）をリセットしない
  // ★ 時間の基準点は bill.opened_at で固定、セット追加は合計分数を延ばすだけ
  // ★ emit('update-times') を削除し、opened_at をサーバ側の既存値に任せる

  // 単一ラベル（選択したセット）のコードを使い、合計人数で1行追加（後段で master_id 解決）
  const lines = [
    { type: 'set', code: selectedMaster.code, qty: total }
  ]
  if (nightRef.value) {
    lines.push({ type: 'addon', code: 'addonNight', qty: total })
  }
  if (specialRef.value !== 'none') {
    // 割引は既存 DiscountRule の code を discount_code で伝える（行追加はしない）
  }

  emit('applySet', {
    lines,
    config: { night: !!nightRef.value },
    discount_code: (specialRef.value !== 'none') ? String(specialRef.value) : null,
  })
  
  alert('SETを追加しました！')
  // 伝票作成後はinfoタブに遷移
  switchTab('info')
}

const q = ref('')
const doSearch = () => emit('searchCustomer', q.value.trim())

// Multiselect 用の顧客検索
const selectedCustomer = ref(null)

// props.customer が変更されたら selectedCustomer に反映
watch(() => props.customer, (newCustomer) => {
  if (newCustomer && !selectedCustomer.value) {
    selectedCustomer.value = newCustomer
  }
}, { immediate: true })

function onCustomerSearch(query) {
  if (query && query.length > 0) {
    emit('searchCustomer', query)
  }
}
function onCustomerSelect(customer) {
  if (customer) {
    selectedCustomer.value = customer
  }
}
function saveSelectedCustomer() {
  if (selectedCustomer.value) {
    emit('pickCustomer', selectedCustomer.value)
    switchTab('info')
  }
}
function customLabel(customer) {
  if (!customer) return ''
  return customer.alias || customer.full_name || `#${customer.id}`
}
</script>

<template>

  <div class="panel base">

    <nav class="row border-bottom g-1 mb-3">
      <div
      class="col-4"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'first' }">
        <button 
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="switchTab('first')">
          初期入力
        </button>
      </div>
      <div
      class="col-4"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'info' }"  >
        <button 
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="switchTab('info')">
          基本情報
        </button>
      </div>
      <div
      class="col-4"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'customer' }">
        <button
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="switchTab('customer')">
          顧客
        </button>
      </div>
    </nav>

    <div v-show="activeTab === 'first'"
    class="wrap"
    style="height: calc( 100vh - 80px);"
    id="first">
      <h2 class="text-center my-3 fs-5"> 
        初期入力をして<br>
        伝票を作成してください</h2>

      <div class="area mb-4">
        <h3 class="fs-5 fw-bold"><IconUsers />人数</h3>
        <div class="row g-3">
          <!-- 男性 -->
            <div class="col-6">
            <div class="d-flex align-items-center">
              <IconGenderMale class="text-info" stroke-width="1.5"/>
              <div class="cartbutton d-flex align-items-center w-100">
                <div class="d-flex align-items-center justify-content-around bg-light h-auto p-2 m-2 w-100 fs-5" style="border-radius:100px;">
                  <button type="button" @click="dec('male')" :class="{ invisible: qtyOf('male')===0 }">
                    <IconMinus :size="16" />
                  </button>
                  <span>{{ qtyOf('male') }}</span>
                  <button type="button" @click="inc('male')"><IconPlus :size="16" /></button>
                </div>
              </div>
            </div>
          </div>
          <!-- 女性 -->
          <div class="col-6">
            <div class="d-flex align-items-center">
              <IconGenderFemale class="text-danger" stroke-width="1.5"/>
              <div class="cartbutton d-flex align-items-center w-100">
                <div class="d-flex align-items-center justify-content-around bg-light h-auto p-2 m-2 w-100 fs-5" style="border-radius:100px;">
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
      </div>

      <div class="area mb-4">
        <h3 class="fs-5 fw-bold"><IconPinned />テーブル番号</h3>
        <div class="row g-1">
          <div
            v-for="t in filteredTables"
            :key="t.id"
            class="col-4">
            <button
              class="btn w-100"
              :class="tableId === t.id ? 'btn-secondary' : 'btn-outline-secondary'"
              @click="$emit('update:tableId', t.id)">
              {{ t.number }}
            </button>
          </div>
        </div>
      </div>


      <div class="area mb-4">
        <div class="box" v-if="Object.keys(setMasters).length > 0">
          <h3 class="fs-5 fw-bold"><IconSettings2 />セット</h3>
          <div class="d-flex flex-column gap-2 w-100" role="group" aria-label="セット商品">
            <template v-for="m in Object.values(setMasters)" :key="m.id">
              <div class="row align-items-center g-0">
                <div class="col-10">
                  <div class="border p-2 d-flex text-secondary align-items-center justify-content-around w-100">
                    <button type="button" @click="dec('set', m.id)">
                      <IconMinus :size="16" />
                    </button>
                    <span>{{ m.name }}</span>
                    <button type="button" @click="inc('set', m.id)">
                      <IconPlus :size="16" />
                    </button>
                  </div>
                </div>
                <div class="col-2 h-100">
                  <div class="d-flex align-items-center justify-content-center h-100">
                    <span class="fs-4">{{ setQtyMap[m.id] || 0 }}</span>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div class="area mt-auto">
        <button class="btn btn-warning w-100 my-2" @click="applySet">伝票を作成</button>
      </div>
    </div>


    <div v-show="activeTab === 'info'" class="wrap" id="info">
      <!-- 最新の現在着席中キャスト -->
      <div class="now-casts">
        <div class="d-flex p-2 justify-content-between align-items-center">
          <span class="fw-bold">稼働中キャスト</span>
          <div class="d-flex justify-content-end align-items-center gap-1">
            <div class="badge bg-blue df-center">フリー</div><div class="badge bg-success df-center">場内</div><div class="badge bg-purple df-center">ヘルプ</div>
          </div>

        </div>
        <div class="wrap p-3 mb-3 bg-light df-center gap-3">
          <div v-for="c in safeCurrent" :key="c?.id" class="df-center">
            <div 
              class="box df-center rounded py-1 px-2 gap-2 text-white"
              :class="{
                      'bg-danger': c.stay_type==='nom',
                      'bg-success': c.stay_type==='in',
                      'bg-blue': c.stay_type==='free' || !c.stay_type
                    }">
                <Avatar :url="c.avatar_url" :alt="c.stage_name" :size="24" />
                <span class="">{{ c.stage_name }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="area my-2 d-flex flex-column gap-3">
        <!-- 開始時刻 -->
        <div class="row align-items-center border-bottom pb-2">
          <div class="col-3">
            <h3 class="m-0"><IconStopwatch />開始時刻</h3>
          </div>
          <div class="col-6">
            <input v-if="editingStart" type="datetime-local" class="form-control" v-model="editStartLocal" />
            <span v-else class="fs-1 fw-bold">{{ startDisplay }}</span>
          </div>
          <div class="col-3">
            <button v-if="editingStart" class="btn btn-success btn-sm df-center gap-1 w-100" @click="saveEditStart">
              <IconDeviceFloppy />保存
            </button>
            <button v-else class="btn btn-outline-danger btn-sm df-center gap-1 w-100" @click="beginEditStart">
              <IconPencil />編集
            </button>
          </div>
        </div>

        <!-- 終了時刻 -->
        <div class="row align-items-center border-bottom pb-2">
          <div class="col-3">
            <h3 class="m-0"><IconBellPause />終了時刻</h3>
          </div>
          <div class="col-6">
            <input v-if="editingEnd" type="datetime-local" class="form-control" v-model="editEndLocal" />
            <span v-else class="fs-1 fw-bold">{{ endDisplay }}</span>
          </div>
          <div class="col-3">
            <button v-if="editingEnd" class="btn btn-success btn-sm df-center gap-1 w-100" @click="saveEditEnd">
              <IconDeviceFloppy />保存
            </button>
            <button v-else class="btn btn-outline-danger btn-sm df-center gap-1 w-100" @click="beginEditEnd">
              <IconPencil />編集
            </button>
          </div>
        </div>

        <!-- テーブル -->
        <div class="row align-items-center border-bottom pb-2">
          <div class="col-3">
            <h3 class="m-0"><IconPinned/>テーブル</h3>
          </div>
          <div class="col-6">
            <select v-if="editingTable" class="form-select" v-model="editTableLocal">
              <option :value="null">-</option>
              <option v-for="t in filteredTables" :key="t.id" :value="t.id">{{ t.number }}</option>
            </select>
            <span v-else class="fs-1 fw-bold">{{ tableNumberLabel }}</span>
          </div>
          <div class="col-3">
            <button v-if="editingTable" class="btn btn-success btn-sm df-center gap-1 w-100" @click="saveEditTable">
              <IconDeviceFloppy />保存
            </button>
            <button v-else class="btn btn-outline-danger btn-sm df-center gap-1 w-100" @click="beginEditTable">
              <IconPencil />編集
            </button>
          </div>
        </div>

        <!-- 人数 -->
        <div class="row align-items-center border-bottom pb-2">
          <div class="col-3">
            <h3 class="m-0"><IconUsers />人数</h3>
          </div>
          <div class="col-6">
            <input v-if="editingPax" type="number" class="form-control" v-model="editPaxLocal" min="0" />
            <span v-else class="fs-1 fw-bold">{{ paxLabel }}</span>
          </div>
          <div class="col-3">
            <button v-if="editingPax" class="btn btn-success btn-sm df-center gap-1 w-100" @click="saveEditPax">
              <IconDeviceFloppy />保存
            </button>
            <button v-else class="btn btn-outline-danger btn-sm df-center gap-1 w-100" @click="beginEditPax">
              <IconPencil />編集
            </button>
          </div>
        </div>

        <!-- 延長 -->
        <div class="row align-items-center border-bottom pb-2">
          <div class="col-3">
            <h3 class="m-0"><IconRefresh />延長</h3>
          </div>
          <div class="col-6">
            <span class="fs-1 fw-bold">{{ extCountView }}</span>
          </div>
          <div class="col-3">
            <button class="btn btn-outline-danger btn-sm df-center gap-1 w-100" @click="goToPayPanel">
              <IconReceiptYen />確認
            </button>
          </div>
        </div>

        <!-- 顧客 -->
        <div class="row align-items-center">
          <div class="col-3">
            <h3 class="m-0"><IconUser />顧客</h3>
          </div>
          <div class="col-6">
            <span class="fs-4 fw-bold">{{ customerName || '未選択' }}</span>
          </div>
          <div class="col-3">
            <button class="btn btn-outline-danger btn-sm df-center gap-1 w-100" @click="beginEditCustomer">
              <IconPencil />編集
            </button>
          </div>
        </div>
      </div>

      <div class="bg-light py-3 mt-3">
        <div class="df-center fs-5 gap-1"><IconReceiptYen />現在の小計</div>
        <div class="df-center fs-1 fw-bold">
          <span>{{ subtotalFormatted }}</span>
        </div>
      </div>


    </div>


    <div v-show="activeTab === 'customer'" class="wrap p-3" id="customer">

      <!-- 選択中の顧客情報 -->
      <div class="bg-light rounded p-2">
        <div class="text-center fs-5 fw-bold pt-2 mb-3 pb-3 border-bottom">
          <IconUserScan /> 選択中の顧客
        </div>
        <dl class="row g-2 mb-0">
          <dt class="col-4 text-end">名前</dt>
          <dd class="col-8 fw-bold">{{ customerDisplayName }}</dd>
          
          <dt class="col-4 text-end">フルネーム</dt>
          <dd class="col-8">{{ customerFullName }}</dd>
          
          <dt class="col-4 text-end">誕生日</dt>
          <dd class="col-8">{{ customerBirthday }}</dd>
          
          <dt class="col-4 text-end">前回の<br>ご注文</dt>
          <dd class="col-8">{{ customerLastOrder }}</dd>
          
          <dt class="col-4 text-end">前回の<br>来店日時</dt>
          <dd class="col-8">{{ customerLastVisit }}</dd>
          
          <dt class="col-4 text-end">前回の<br>キャスト</dt>
          <dd class="col-8">{{ customerLastCast }}</dd>
          
          <dd class="col-12">
            <p class="mx-2 mb-0 bg-white rounded p-3"  style="min-height: 80px; white-space: pre-wrap;">
              {{ customerMemo }}
            </p>
          </dd>
        </dl>
      </div>

      <!-- 顧客検索 UI (Vue Multiselect) -->
      <div class="mt-4">
        <div class="text-center fs-5 fw-bold mb-3">
          <IconUserScan />顧客を検索＆選択し直す
        </div>
        <Multiselect
          v-model="selectedCustomer"
          :options="customerResults"
          :custom-label="customLabel"
          placeholder="名前・TEL・あだ名で検索"
          label="alias"
          track-by="id"
          :searchable="true"
          :internal-search="false"
          :loading="customerSearching"
          :clear-on-select="false"
          :close-on-select="true"
          :options-limit="20"
          :show-no-results="true"
          select-label=""
          deselect-label=""
          @search-change="onCustomerSearch"
          @select="onCustomerSelect"
        >
          <template #noResult>検索結果がありません</template>
          <template #noOptions>...</template>
        </Multiselect>
        
        <button 
          v-if="selectedCustomer"
          class="btn btn-primary w-100 mt-3"
          @click="saveSelectedCustomer">
          <IconDeviceFloppy /> この顧客を保存
        </button>
      </div>

    </div>


  </div>

</template>


<style lang="scss">
  #first{
    &.wrap{
      h3{
        font-size: 1rem;
        font-weight: bold;
        display: flex;
        align-items: center;
        gap: 4px;
        margin-bottom: 1rem;
      }
    }
  }


  #info{
    &.wrap{
      h3{
        font-size: 0.8rem;
        font-weight: normal;
        display: flex;
        align-items: center;
        gap: 4px;
        margin-bottom: 1rem;
      }
    }
  }

  #customer{
    &.wrap{
      h3{
        font-size: 1.2rem;
        font-weight: normal;
        display: flex;
        align-items: center;
        gap: 4px;
      }
      dl{
        dt{
          font-weight: bold;
        }
      }
      .multiselect{
        &__single{
          font-size: 1rem;
        }
        &__tags{
          border-color: #333;
        }
        &__option--highlight{
          background: #333;
          &:after{
            background: #333;
          }
        }
        &__option--selected{
          background: #f3f3f3;
          color: #333;
          &:after{
            background: #333;
          }
        }
        &__tag{
          background: #333;
        }
        &__tag-icon{
          &:after{
            color: #333;
          }
          &:hover{
            background: #222;
          }
        }
      }
    }
  }
</style>