<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import Avatar from '@/components/Avatar.vue'
import TablePicker from '@/components/TablePicker.vue'
import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'
import { fetchBasicDiscountRules, fetchDiscountRules, fetchStoreSeatSettings, fetchMasters, fetchBillTags, fetchCustomers, patchBill, api } from '@/api'  // ← api 追加
import { useBillCustomers } from '@/composables/useBillCustomers'
import { useBillCustomerTimeline } from '@/composables/useBillCustomerTimeline'

const props = defineProps({
  billId: { type: [Number, null], default: null },
  tables: { type: Array, default: () => [] },
  tableId: { type: [Number, null], default: null },
  tableIds: { type: Array, default: () => [] },

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

  // 税・サービス料（ON=加算）
  applyService: { type: Boolean, default: true },
  applyTax: { type: Boolean, default: true },
  
  // メモ
  memo: { type: String, default: '' },
  // 伝票の表示名（あだ名）
  displayName: { type: String, default: '' },
  
  // タグ
  tags: { type: Array, default: () => [] },  // BillTag オブジェクトの配列
  selectedTagIds: { type: Array, default: () => [] },  // 選択済みのタグ ID リスト
  
  // 親から渡された bill customers（優先使用）
  billCustomersFromParent: { type: Array, default: null },
})

const emit = defineEmits([
  'update:seatType','update:tableId','update:tableIds','update:pax',
  'update:applyService','update:applyTax','update:memo','update:display-name',
  'update:selectedTagIds',  // ← 追加
  'chooseCourse','clearCustomer','searchCustomer','pickCustomer',
  'applySet','save','switchPanel','update-times'
])

/* ===== 席種・テーブル ===== */
const seatTypeRef  = ref(props.seatType || 'main')
watch(() => props.seatType, v => { seatTypeRef.value = v || 'main' })

const applyServiceModel = computed({
  get: () => !!props.applyService,
  set: (v) => emit('update:applyService', !!v)
})
const applyTaxModel = computed({
  get: () => !!props.applyTax,
  set: (v) => emit('update:applyTax', !!v)
})

// メモの双方向バインディング
const memoLocal = ref(props.memo || '')
watch(() => props.memo, (v) => { memoLocal.value = v || '' }, { immediate: true })
watch(memoLocal, (v) => { emit('update:memo', v) })

// 伝票の表示名（あだ名）の双方向バインディング
const displayNameLocal = ref(props.displayName || '')
watch(() => props.displayName, (v) => { displayNameLocal.value = v || '' }, { immediate: true })
watch(displayNameLocal, (v) => { emit('update:display-name', v) })

// タグ関連
const selectedTagIds = ref(props.selectedTagIds || [])
watch(() => props.selectedTagIds, (v) => { selectedTagIds.value = v || [] }, { immediate: true })

const toggleTag = (tagId) => {
  const idx = selectedTagIds.value.indexOf(tagId)
  if (idx >= 0) {
    selectedTagIds.value.splice(idx, 1)
  } else {
    selectedTagIds.value.push(tagId)
  }
  // 直接 emit（watch ではなく、click ハンドラから直接呼び出す）
  emit('update:selectedTagIds', Array.from(selectedTagIds.value))
}

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

// Bill customers management
const billCustomersComp = useBillCustomers()
const timelineComp = useBillCustomerTimeline()

const billCustomers = ref([])
const loadingBillCustomers = ref(false)
const billCustomersError = ref('')

const editArrivedLocal = ref({})
const editLeftLocal = ref({})
const editingBillCustomerArrived = ref({})  // bcId -> true/false（入店）
const editingBillCustomerLeft = ref({})     // bcId -> true/false（退店）

function toLocalInput(iso) {
  return iso ? dayjs(iso).format('YYYY-MM-DDTHH:mm') : ''
}
function toISOFromLocal(v) {
  return v ? dayjs(v).toISOString() : null
}

function beginEditBillCustomerArrived(bcId) {
  editingBillCustomerArrived.value[bcId] = true
}

function cancelEditBillCustomerArrived(bcId) {
  const bc = billCustomers.value.find(b => b.id === bcId)
  if (bc) {
    editArrivedLocal.value[bcId] = toLocalInput(bc.arrived_at)
  }
  editingBillCustomerArrived.value[bcId] = false
}

function beginEditBillCustomerLeft(bcId) {
  editingBillCustomerLeft.value[bcId] = true
}

function cancelEditBillCustomerLeft(bcId) {
  const bc = billCustomers.value.find(b => b.id === bcId)
  if (bc) {
    editLeftLocal.value[bcId] = toLocalInput(bc.left_at)
  }
  editingBillCustomerLeft.value[bcId] = false
}

async function refreshBillCustomers() {
  if (!props.billId) return
  
  // 【修正】親からbillCustomersが渡されている場合はそれを使用
  if (props.billCustomersFromParent !== null && Array.isArray(props.billCustomersFromParent)) {
    billCustomers.value = [...props.billCustomersFromParent]
    
    if (import.meta.env.DEV) {
      console.log(`[BasicsPanel] 親からのbillCustomersを使用:`, {
        billId: props.billId,
        '顧客数': billCustomers.value.length,
        '顧客ID一覧': billCustomers.value.map(bc => bc.id)
      })
    }
    return
  }
  
  // 親から渡されていない場合は自分で取得
  loadingBillCustomers.value = true
  billCustomersError.value = ''
  try {
    await billCustomersComp.fetchBillCustomers(props.billId)
    
    // 【フェーズ5】明示的に新しい配列を作成してリアクティビティを確実にする
    const freshList = billCustomersComp.customers.value || []
    billCustomers.value = [...freshList]  // スプレッド演算子で新配列作成
    
    // 【フェーズ5】詳細デバッグログ（DEV環境のみ）
    if (import.meta.env.DEV) {
      console.log(`[フェーズ5] refreshBillCustomers完了:`, {
        billId: props.billId,
        'billCustomers.length': billCustomers.value.length,
        'APIから取得した件数': freshList.length,
        '配列が更新されたか': billCustomers.value !== freshList,
        '顧客ID一覧': billCustomers.value.map(bc => bc.id)
      })
    }
  } catch (e) {
    console.warn('[BasicsPanel] fetch bill customers failed', e)
    billCustomersError.value = '顧客の取得に失敗しました'
    billCustomers.value = []
  } finally {
    loadingBillCustomers.value = false
  }
}

watch(() => props.billId, async (id) => {
  if (!id) return
  await refreshBillCustomers()
}, { immediate: true })

// 親からbillCustomersが渡された場合はそれを反映
watch(() => props.billCustomersFromParent, (newVal) => {
  if (newVal !== null && Array.isArray(newVal)) {
    billCustomers.value = [...newVal]
    if (import.meta.env.DEV) {
      console.log('[BasicsPanel] billCustomersFromParentが更新されました:', newVal.length)
    }
  }
}, { deep: true })

watch(billCustomers, async (list, oldList) => {
  // 【フェーズ5】watch発火のデバッグログ
  if (import.meta.env.DEV) {
    console.log(`[フェーズ5] watch(billCustomers)発火:`, {
      '新しい件数': list?.length || 0,
      '前回の件数': oldList?.length || 0,
      '増減': (list?.length || 0) - (oldList?.length || 0),
      '顧客ID一覧': list?.map(bc => bc.id) || []
    })
  }
  
  const a = {}
  const l = {}
  for (const bc of (list || [])) {
    a[bc.id] = toLocalInput(bc.arrived_at)
    l[bc.id] = toLocalInput(bc.left_at)
  }
  editArrivedLocal.value = a
  editLeftLocal.value = l
  
  // 【フェーズ2】初期状態で最初の顧客を自動選択（未選択の場合）
  if (list.length > 0) {
    // 選択中のIDが存在しない、またはリストに含まれない場合は先頭を選択
    const hasSelected = list.some(bc => bc.id === selectedBillCustomerId.value)
    if (!hasSelected) {
      selectedBillCustomerId.value = list[0].id
      await selectBillCustomer(list[0])
    }
  } else {
    selectedBillCustomerId.value = null
    selectedBillCustomer.value = null
  }
}, { deep: true })

const addingGuest = ref(false)

function addGuestToBill() {
  // フェーズ1：confirm で注意を表示して初期入力タブへ誘導
  const confirmed = confirm(
    'お客様を増やすとSET（料金）も増やす必要があります。\n\n' +
    '先に「初期入力」で人数とSETを増やしてから追加してください。\n\n' +
    '初期入力に移動しますか？'
  )
  
  if (confirmed) {
    switchTab('first')
  }
}

async function saveCustomerTimes(bcId) {
  const arrived_at = toISOFromLocal(editArrivedLocal.value[bcId])
  const left_at = toISOFromLocal(editLeftLocal.value[bcId])
  try {
    await billCustomersComp.updateBillCustomer(bcId, { arrived_at, left_at })
    await refreshBillCustomers()
  } catch (e) {
    alert('時刻の保存に失敗しました（INより前にOUTなど）')
  }
}

// 顧客差し替え機能
const allCustomersForReplace = ref([])
const replaceCustomerMap = ref({})  // bcId -> customerId
const replacingBillCustomerId = ref(null)
const editingReplaceCustomer = ref({})  // bcId -> boolean（編集モード）

// 既存顧客リストを取得（初回のみ）
async function loadCustomersForReplace() {
  try {
    const data = await fetchCustomers()
    // results か直接の配列か判定
    allCustomersForReplace.value = data.results || data || []
  } catch (e) {
    console.warn('[BasicsPanel] load customers for replace failed', e)
    allCustomersForReplace.value = []
  }
}

function beginEditReplaceCustomer(bcId) {
  editingReplaceCustomer.value[bcId] = true
}

function cancelEditReplaceCustomer(bcId) {
  replaceCustomerMap.value[bcId] = ''
  editingReplaceCustomer.value[bcId] = false
}

function updateReplaceCustomer(bcId) {
  // dropdown が変わったら、新しい customer を select（既に replaceCustomerMap に反映）
  // 特に処理なし（差し替えボタンを押すまで待つ）
}

async function replaceCustomer(bcId) {
  const newCustomerId = replaceCustomerMap.value[bcId]
  if (!newCustomerId) return

  replacingBillCustomerId.value = bcId

  try {
    await billCustomersComp.updateBillCustomer(bcId, { customer: newCustomerId })
    replaceCustomerMap.value[bcId] = ''  // reset dropdown
    editingReplaceCustomer.value[bcId] = false  // 編集モード解除
    await refreshBillCustomers()
    alert('顧客を差し替えました')
  } catch (e) {
    console.error('[BasicsPanel] replace customer failed', e)
    alert(`顧客の差し替えに失敗しました: ${e?.response?.data?.customer?.[0] || e?.message || ''}`)
  } finally {
    replacingBillCustomerId.value = null
  }
}

onMounted(async () => {
  // 顧客リスト読み込み（差し替え用）
  await loadCustomersForReplace()
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

// 【フェーズ1】男/女変更時は即座に親に通知しない（ローカル状態のみ更新）
// pax反映は「更新」ボタン押下時のみ行う

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
const editingDisplayName = ref(false)
const editingCustomer = ref(false)

// 編集用ローカル値
const editStartLocal = ref('')
const editEndLocal = ref('')
const editTableIdsLocal = ref([])
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
  // 優先：props.tableIds（複数）
  if (Array.isArray(props.tableIds) && props.tableIds.length) {
    editTableIdsLocal.value = props.tableIds.map(Number)
  } else if (props.tableId != null) {
    // 互換：単一しか無い場合
    editTableIdsLocal.value = [Number(props.tableId)]
  } else {
    editTableIdsLocal.value = []
  }
  editingTable.value = true
}
function saveEditTable() {
  const ids = (editTableIdsLocal.value || [])
    .map(Number)
    .filter(v => Number.isFinite(v))

  // 複数の真実
  emit('update:tableIds', ids)

  // legacy互換（先頭を tableId にも反映）
  emit('update:tableId', ids.length ? ids[0] : null)

  editingTable.value = false
}

// 人数編集
function beginEditPax() {
  editPaxLocal.value = Number(props.pax) || 0
  editingPax.value = true
}
async function saveEditPax() {
  const newPax = Number(editPaxLocal.value) || 0
  editingPax.value = false
  
  // 【フェーズ1】既存伝票の場合は即座にAPI更新
  if (props.billId) {
    try {
      await patchBill(props.billId, { pax: newPax })
      emit('update:pax', newPax)
      
      // 【フェーズ1】pax更新後に顧客リストを再取得
      await refreshBillCustomers()
      
      if (import.meta.env.DEV) {
        console.log(`[フェーズ1] 人数編集保存完了:`, {
          billId: props.billId,
          newPax,
          '顧客数': billCustomers.value.length
        })
      }
    } catch (e) {
      console.error('[BasicsPanel] pax update failed:', e)
      alert('人数の更新に失敗しました')
    }
  } else {
    // 新規伝票の場合はローカル状態のみ更新
    emit('update:pax', newPax)
  }
  
  // 【フェーズ0】pax更新後の真実確認ログは削除（フェーズ1で統合）
}

// 延長→会計パネルへ
function goToPayPanel() {
  emit('switchPanel', 'pay')
}

// 伝票の表示名（あだ名）編集
function beginEditDisplayName() {
  editingDisplayName.value = true
}
function saveEditDisplayName() {
  editingDisplayName.value = false
  // displayNameLocal は既に watch で emit('update:displayName', v) しているので、ここでは特に追加の処理は不要
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
  // 1) 複数（props.tableIds）
  const ids = Array.isArray(props.tableIds)
    ? props.tableIds.map(Number).filter(Boolean)
    : []
  if (ids.length) {
    const labels = ids
      .map(id => safeTables.value.find(t => Number(t.id) === Number(id))?.number)
      .filter(Boolean)
    return labels.length ? labels.join(' + ') : ids.join(' + ')
  }

  // 2) 互換（props.tableId）
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
  if (selectedBillCustomer.value) return selectedBillCustomer.value.alias || selectedBillCustomer.value.full_name || `#${selectedBillCustomer.value.id}`
  if (selectedCustomer.value) return selectedCustomer.value.alias || selectedCustomer.value.full_name || `#${selectedCustomer.value.id}`
  if (!props.customer) return 'ご新規様'
  return props.customer.alias || props.customer.full_name || `#${props.customer.id}`
})

// 代表顧客（優先順位：props.customer → billCustomers[0] → null）
const representativeCustomer = computed(() => {
  // 1. 顧客マスタが選択されている場合はそれを優先
  if (props.customer || selectedCustomer.value) return null // props.customer優先なのでnullを返す（表示は従来通り）
  // 2. 卓内の客が存在する場合は先頭を代表として扱う
  if (billCustomers.value && billCustomers.value.length > 0) {
    return billCustomers.value[0]
  }
  // 3. どちらも無ければnull
  return null
})

// 代表顧客の表示名
const representativeCustomerDisplay = computed(() => {
  const bc = representativeCustomer.value
  if (!bc) return null
  // BillCustomerの表示名またはGuest-XXXXXX
  const cid = bc.customer || bc.customer_id
  return bc.display_name || bc.customer_name || (cid != null ? `Guest-${String(cid).padStart(6, '0')}` : 'Guest')
})

// 代表顧客の入店時刻（BillCustomer由来の場合のみ）
const representativeArrivedAt = computed(() => {
  const bc = representativeCustomer.value
  if (!bc || !bc.arrived_at) return null
  return bc.arrived_at
})

// 代表顧客の退店時刻（BillCustomer由来の場合のみ）
const representativeLeftAt = computed(() => {
  const bc = representativeCustomer.value
  if (!bc || !bc.left_at) return null
  return bc.left_at
})

const customerFullName = computed(() => {
  const c = selectedBillCustomer.value || selectedCustomer.value || props.customer
  if (!c) return '-'
  return c.full_name || '-'
})

const customerBirthday = computed(() => {
  const c = selectedBillCustomer.value || selectedCustomer.value || props.customer
  if (!c?.birthday) return '-'
  return dayjs(c.birthday).format('YYYY年MM月DD日')
})

const customerLastOrder = computed(() => {
  const c = selectedBillCustomer.value || selectedCustomer.value || props.customer
  if (!c?.last_order) return '-'
  return c.last_order
})

const customerLastVisit = computed(() => {
  const c = selectedBillCustomer.value || selectedCustomer.value || props.customer
  if (!c?.last_visit_at) return '-'
  return dayjs(c.last_visit_at).format('YYYY/MM/DD HH:mm')
})

const customerLastCast = computed(() => {
  const c = selectedBillCustomer.value || selectedCustomer.value || props.customer
  if (!c?.last_cast_name) return '-'
  return c.last_cast_name
})

const customerMemo = computed(() => {
  const c = selectedBillCustomer.value || selectedCustomer.value || props.customer
  if (!c?.memo) return 'メモなし'
  return c.memo
})

/* 追加（黄色ボタン） */
function applySet(){
  const m = Number(maleRef.value||0), f = Number(femaleRef.value||0)
  const paxTotal = m + f
  if (paxTotal <= 0) { alert('人数を入力してください'); return }
  
  // setQtyMap から数量が1以上のセット商品を全部拾う（複数対応）
  const selectedSets = Object.entries(setQtyMap.value)
    .filter(([id, qty]) => Number(qty) > 0)
    .map(([id, qty]) => ({ id: String(id), qty: Number(qty) }))
  
  if (selectedSets.length === 0) { alert('セット商品を選択してください'); return }

  const lines = []

  // ★ セットは「選んだ数」だけ追加する（paxは掛けない）
  for (const s of selectedSets) {
    const master = setMasters.value[s.id]
    if (!master) continue
    lines.push({ type: 'set', code: master.code, qty: s.qty })

    // ★ 深夜アドオンも「セットと同数」で追加（仕様が人数分ならここは変える）
    if (nightRef.value) {
      lines.push({ type: 'addon', code: 'addonNight', qty: s.qty })
    }
  }

  // 【フェーズ1】paxも一緒に送信
  emit('applySet', {
    lines,
    pax: paxTotal,  // 人数を含める
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

// 顧客ブロックから選択した顧客（詳細情報取得済み）
const selectedBillCustomer = ref(null)

// 【フェーズ2】選択中のBillCustomer ID（ラジオ的選択）
const selectedBillCustomerId = ref(null)

// props.customer が変更されたら selectedCustomer に反映
watch(() => props.customer, (newCustomer) => {
  if (newCustomer && !selectedCustomer.value) {
    selectedCustomer.value = newCustomer
  }
}, { immediate: true })

// 【フェーズ2】顧客ブロックの名前をタップして顧客情報を詳細表示
async function selectBillCustomer(bc) {
  try {
    // 【フェーズ2】選択状態を更新（ラジオ的）
    selectedBillCustomerId.value = bc.id
    
    // 顧客マスタから詳細情報を取得
    const customerId = bc.customer || bc.customer_id
    if (!customerId) {
      selectedBillCustomer.value = null
      return
    }
    
    // 【フェーズ2】fetchCustomer単体取得を試みる（軽量化）
    // api.jsに単体取得がない場合は全件取得にフォールバック
    try {
      const { data } = await api.get(`/billing/customers/${customerId}/`)
      selectedBillCustomer.value = data
    } catch (e) {
      // フォールバック: 全件取得して探す
      const data = await fetchCustomers()
      const customers = data.results || data || []
      const customer = customers.find(c => Number(c.id) === Number(customerId))
      selectedBillCustomer.value = customer || null
    }
  } catch (e) {
    console.warn('[BasicsPanel] selectBillCustomer failed', e)
    selectedBillCustomer.value = null
  }
}

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
      <div v-if="props.openedAt" class="alert alert-info alert-sm my-2 mx-2 p-2" role="alert">
        <small>
          <strong>お客様を増やす場合：</strong> 人数とSETを増やしてから「伝票を作成」を押してください。
        </small>
      </div>

      <h2 class="text-center my-3 fs-5"> 
        初期入力をして<br>
        伝票を作成してください</h2>

      <div class="area mb-5">
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

      <div class="area mb-5">
        <h3 class="fs-5 fw-bold"><IconPinned />複数テーブル選択</h3>
        <TablePicker
          :tables="filteredTables"
          :modelValue="tableIds"
          :multiple="true"
          labelKey="number"
          colClass="col-4"
          @update:modelValue="v => $emit('update:tableIds', v)"
        />
      </div>

      <div class="area mb-5">
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

      <div class="area mb-5">
        <h3 class="fs-5 fw-bold mb-0"><IconAdjustments />チャージ</h3>
        <small class="text-muted mb-3">オフでカットできます</small>

        <div class="df-center justify-content-start gap-4 mt-3">
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" id="switch-service" v-model="applyServiceModel">
            <label class="form-check-label" for="switch-service">サービス料を追加</label>
          </div>
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" id="switch-tax" v-model="applyTaxModel">
            <label class="form-check-label" for="switch-tax">TAXを追加</label>
          </div>
        </div>
      </div>

      <div class="area mb-5">
        <h3 class="fs-5 fw-bold"><IconLabel />関係店</h3>

        <div class="df-center justify-content-start gap-4 mt-3 flex-wrap">
          <template v-if="tags && tags.length">
            <button
              v-for="tag in tags"
              :key="tag.id"
              type="button"
              :class="selectedTagIds.includes(tag.id) ? 'btn btn-primary' : 'btn btn-outline-primary'"
              @click="toggleTag(tag.id)"
            >
              {{ tag.name }}
            </button>
          </template>
          <small v-else class="text-muted">タグはまだありません</small>
        </div>
      </div>

      <!-- 伝票の表示名（あだ名） -->
      <div class="area mb-3">
        <label class="form-label fw-bold">伝票の表示名</label>
        <input
          class="form-control"
          v-model="displayNameLocal"
          placeholder="例：AB1 / AB2 / VIP来店"
        />
      </div>

      <!-- メモ -->
      <div class="area mb-5">
        <h3 class="fs-5 fw-bold"><IconNote />メモ</h3>
        <textarea class="form-control" rows="3" v-model="memoLocal" placeholder="伝票情報や割引などをメモしてください"></textarea>
      </div>

      <div v-if="props.openedAt" class="area mt-auto">
        <button class="btn btn-warning w-100 my-2" @click="applySet">更新</button>
      </div>
      <div v-else class="area mt-auto">
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
        <!-- 伝票名 -->
        <div class="row align-items-center border-bottom pb-2">
          <div class="col-3">
            <h3 class="m-0"><IconStopwatch />伝票名</h3>
          </div>
          <div class="col-6">
            <input v-if="editingDisplayName" type="text" class="form-control" v-model="displayNameLocal" placeholder="例：AB1 / AB2 / VIP来店" />
            <span v-else class="fs-1 fw-bold">{{ displayNameLocal || '-' }}</span>
          </div>
          <div class="col-3">
            <button v-if="editingDisplayName" class="btn btn-success btn-sm df-center gap-1 w-100" @click="saveEditDisplayName">
              <IconDeviceFloppy />保存
            </button>
            <button v-else class="btn btn-outline-danger btn-sm df-center gap-1 w-100" @click="beginEditDisplayName">
              <IconPencil />編集
            </button>
          </div>
        </div>
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
            <div v-if="editingTable">
              <TablePicker
                :tables="filteredTables"
                :modelValue="editTableIdsLocal"
                :multiple="true"
                labelKey="number"
                colClass="col-4"
                @update:modelValue="v => (editTableIdsLocal = v)"
              />
            </div>
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
        <div class="row align-items-start">
          <div class="col-3">
            <h3 class="m-0"><IconUser />顧客</h3>
          </div>
          <div class="col-9">
            <div v-if="!billCustomers.length" class="text-muted small">
              {{ customerName || '未選択' }}
            </div>
            <!-- 【フェーズ2】ラジオ風チップ表示 -->
            <div v-else class="d-flex flex-wrap gap-2">
              <button
                v-for="bc in billCustomers"
                :key="bc.id"
                type="button"
                class="btn btn-sm"
                :class="selectedBillCustomerId === bc.id ? 'btn-primary' : 'btn-outline-secondary'"
                @click="selectBillCustomer(bc)"
              >
                <span class="fw-bold">{{ bc.display_name || bc.customer_name || 'Guest' }}</span>
                <span v-if="bc.arrived_at" class="ms-1 small">({{ dayjs(bc.arrived_at).format('HH:mm') }}~)</span>
              </button>
            </div>
            <button class="btn btn-outline-danger btn-sm df-center gap-1 w-100 mt-2" @click="beginEditCustomer">
              <IconPencil />編集
            </button>
          </div>
        </div>

        <!-- 卓内の客（追加 / IN-OUT編集） -->
        <div class="border-top pt-3 mt-2">
          <div class="d-flex align-items-center justify-content-between">
            <button
              class="btn btn-warning btn-sm w-100"
              type="button"
              :disabled="!props.billId"
              @click="addGuestToBill"
            >
              ＋お客様を追加
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


    <div v-show="activeTab === 'customer'" class="wrap" id="customer">
      <!-- 卓内の客一覧（IN/OUT編集） -->
      <div class="mb-4">
        <h5 class="fw-bold mb-3"><IconUsers /> 着席中のお客様</h5>
        <div v-if="loadingBillCustomers" class="text-muted small">読み込み中...</div>
        <div v-else-if="!billCustomers.length" class="text-muted small">お客様がいません</div>
        <div v-else class="d-flex flex-column gap-3">
          <div v-for="bc in billCustomers" :key="bc.id" class="area my-2 d-flex flex-column gap-3">
            <!-- <div class="small text-muted mb-2">顧客ID: {{ bc.customer || bc.customer_id }}</div> -->
            <div class="row align-items-center border-bottom pb-2">
              <div class="col-2">
                名前
              </div>
              <div class="col-7">
                <!-- 【フェーズ2】タップで選択、選択中をハイライト -->
                <div 
                  class="fw-bold fs-5 cursor-pointer"
                  :class="selectedBillCustomerId === bc.id ? 'text-primary' : 'text-secondary'"
                  @click="selectBillCustomer(bc)"
                  style="cursor: pointer; text-decoration: underline;">
                 {{ bc.display_name || bc.customer_name || 'Guest' }}様
                 <span v-if="selectedBillCustomerId === bc.id" class="badge bg-primary ms-2">選択中</span>
                </div>
                
                <div v-if="editingReplaceCustomer[bc.id]" class="d-flex gap-2 align-items-center flex-column mt-2">
                  <Multiselect
                    :model-value="replaceCustomerMap[bc.id] ? allCustomersForReplace.find(c => String(c.id) === String(replaceCustomerMap[bc.id])) : null"
                    :options="allCustomersForReplace"
                    :custom-label="customLabel"
                    placeholder="既存顧客から検索＆選択"
                    label="alias"
                    track-by="id"
                    :searchable="true"
                    :internal-search="true"
                    :clear-on-select="true"
                    :close-on-select="true"
                    :options-limit="20"
                    :show-no-results="true"
                    select-label=""
                    deselect-label=""
                    @update:model-value="(cust) => { replaceCustomerMap[bc.id] = cust ? String(cust.id) : '' }"
                  >
                    <template #noResult>検索結果がありません</template>
                    <template #noOptions>顧客が見つかりません</template>
                  </Multiselect>
                  <button
                    v-if="replaceCustomerMap[bc.id]"
                    class="btn btn-warning btn-sm whitespace-nowrap w-100"
                    type="button"
                    @click="replaceCustomer(bc.id)"
                    :disabled="replacingBillCustomerId === bc.id"
                  >
                    {{ replacingBillCustomerId === bc.id ? '変更中...' : '差し替え' }}
                  </button>
                </div>
              </div>
              <div class="col-3">
                <button
                  v-if="!editingReplaceCustomer[bc.id]"
                  class="btn btn-outline-danger btn-sm w-100"
                  type="button"
                  @click="beginEditReplaceCustomer(bc.id)"
                >
                  編集
                </button>
                <button
                  v-else
                  class="btn btn-outline-secondary btn-sm w-100 px-0"
                  type="button"
                  @click="cancelEditReplaceCustomer(bc.id)"
                >
                  キャンセル
                </button>
              </div>
            </div>

            <!-- 入店 -->
            <div class="row align-items-center border-bottom pb-2">
              <div class="col-2">
                <span>入店</span>
              </div>
              <div class="col-7">
                <span v-if="!editingBillCustomerArrived[bc.id]" class="fw-bold fs-1">
                  {{ editArrivedLocal[bc.id] ? dayjs(editArrivedLocal[bc.id]).format('HH:mm') : '-' }}
                </span>
                <input
                  v-else
                  type="datetime-local"
                  class="form-control form-control-sm"
                  v-model="editArrivedLocal[bc.id]"
                />
              </div>
              <div class="col-3">
                <button 
                  v-if="!editingBillCustomerArrived[bc.id]"
                  class="btn btn-outline-danger btn-sm w-100" 
                  type="button"
                  @click="beginEditBillCustomerArrived(bc.id)"
                >
                  編集
                </button>
                <button 
                  v-else
                  class="btn btn-success btn-sm w-100" 
                  type="button"
                  @click="saveCustomerTimes(bc.id); editingBillCustomerArrived[bc.id] = false"
                >
                  保存
                </button>
              </div>
            </div>

            <!-- 退店 -->
            <div class="row align-items-center border-bottom pb-2">
              <div class="col-2">
                <span>退店</span>
              </div>
              <div class="col-7">
                <span v-if="!editingBillCustomerLeft[bc.id]" class="fw-bold fs-1">
                  {{ editLeftLocal[bc.id] ? dayjs(editLeftLocal[bc.id]).format('HH:mm') : '-' }}
                </span>
                <input
                  v-else
                  type="datetime-local"
                  class="form-control form-control-sm"
                  v-model="editLeftLocal[bc.id]"
                />
              </div>
              <div class="col-3">
                <button 
                  v-if="!editingBillCustomerLeft[bc.id]"
                  class="btn btn-outline-danger btn-sm w-100" 
                  type="button"
                  @click="beginEditBillCustomerLeft(bc.id)"
                >
                  編集
                </button>
                <button 
                  v-else
                  class="btn btn-success btn-sm w-100" 
                  type="button"
                  @click="saveCustomerTimes(bc.id); editingBillCustomerLeft[bc.id] = false"
                >
                  保存
                </button>
              </div>
            </div>


            <div class="d-flex gap-2 flex-wrap">
              <button class="btn btn-outline-secondary btn-sm" type="button" @click="timelineComp.markArrived(bc.id).then(refreshBillCustomers)">
                今入店
              </button>
              <button class="btn btn-outline-secondary btn-sm" type="button" @click="timelineComp.markLeft(bc.id).then(refreshBillCustomers)">
                今退店
              </button>
              <button class="btn btn-outline-secondary btn-sm" type="button" @click="timelineComp.clearLeft(bc.id).then(refreshBillCustomers)">
                退店解除
              </button>
              <button class="btn btn-success btn-sm" type="button" @click="saveCustomerTimes(bc.id)">
                保存
              </button>
            </div>

          </div>
        </div>
      </div>

      <!-- 選択中の顧客情報 -->

      <div class="bg-light rounded p-2 mb-5">
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