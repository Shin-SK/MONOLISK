<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import Avatar from '@/components/Avatar.vue'
import { fetchBasicDiscountRules, fetchDiscountRules, fetchStoreSeatSettings, fetchMasters } from '@/api'  // ← 追加

const props = defineProps({
  tables: { type: Array, default: () => [] },
  tableId: { type: [Number, null], default: null },

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

const miniTab = ref('customer')


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
  const total = m + f
  if (!selectedSet.value) { alert('セット商品を選択してください'); return }
  if (total <= 0) { alert('人数を入力してください'); return }

  // 開始時間が未設定の場合、現在時刻を設定
  if (!startISO.value) {
    const nowISO = dayjs().toISOString()
    startISO.value = nowISO
    startLocal.value = dayjs(nowISO).format('YYYY-MM-DDTHH:mm')
    emit('update-times', { opened_at: nowISO, expected_out: null })
  }

  const selectedMaster = setMasters.value[selectedSet.value]
  if (!selectedMaster) { alert('セット商品情報が取得できません'); return }

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

        <!-- SET商品選択（上のボックスと同じデザイン）※マスタがない場合は非表示 -->
        <div class="box" v-if="Object.keys(setMasters).length > 0">
          <div class="title"><IconSettings2 /> セット</div>
          <div class="btn-group flex-wrap gap-2 w-100" role="group" aria-label="セット商品">
            <template v-for="m in Object.values(setMasters)" :key="m.id">
              <input class="btn-check" type="radio" name="set-master" :id="`set-${m.id}`"
                     :value="String(m.id)" :checked="selectedSet===String(m.id)"
                     @change="selectedSet = String(m.id)">
              <label class="btn btn-sm"
                     :class="selectedSet===String(m.id) ? 'btn-secondary' : 'btn-outline-secondary'"
                     :for="`set-${m.id}`">
                {{ m.name }}
                <!-- <span class="ms-1">{{ m.price_regular }}円/人</span> -->
              </label>
            </template>
          </div>
        </div>

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
        <!-- ここにセットの種類がラベルとして出てくる -->
        <!-- <div class="wrap w-100 my-3">
          <div class="btn-group flex-wrap gap-2 w-100" role="group" aria-label="特例">
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
        </div> -->


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
          </div>
        </div>

        <button class="btn btn-warning w-100 my-2" @click="applySet">伝票を作成</button>
        

      <!-- 顧客 / 履歴 トグル -->
      <div class="btn-group w-100 mb-2" role="group">
        <button type="button"
                class="btn btn-sm"
                :class="miniTab==='customer' ? 'btn-secondary' : 'btn-outline-secondary'"
                @click="miniTab='customer'">
          顧客
        </button>
        <button type="button"
                class="btn btn-sm"
                :class="miniTab==='history' ? 'btn-secondary' : 'btn-outline-secondary'"
                @click="miniTab='history'">
          着席履歴
        </button>
      </div>

      <!-- 顧客 -->
      <div class="box" v-show="miniTab==='customer'">
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

      <!-- 着席履歴（PCと同等のミニ版） -->
      <div class="box" v-show="miniTab==='history'">
        <div class="title"><IconHistoryToggle /> 着席履歴</div>
        <template v-if="(props.historyEvents || []).length === 0">
          <p class="text-muted mb-0">履歴はありません</p>
        </template>
        <ul v-else class="list-unstyled mb-0 overflow-auto" style="max-height: 160px;">
          <li v-for="ev in props.historyEvents" :key="ev.key"
              class="d-flex align-items-center gap-2 mb-1">
            <small class="text-muted" style="width:40px;">
              {{ dayjs(ev.when).format('HH:mm') }}
            </small>
            <Avatar :url="ev.avatar" :alt="ev.name" :size="24" class="me-1" />
            <span class="flex-grow-1">{{ ev.name }}</span>
            <span class="badge text-white me-1"
                  :class="{
                    'bg-danger': ev.stayTag==='nom',
                    'bg-success': ev.stayTag==='in',
                    'bg-secondary': ev.stayTag==='free' || !ev.stayTag
                  }">
              {{ ev.stayTag==='nom' ? '本指名' : ev.stayTag==='in' ? '場内' : 'フリー' }}
            </span>
            <span class="badge" :class="ev.ioTag==='in' ? 'bg-primary' : 'bg-dark'">
              {{ (ev.ioTag || '').toUpperCase() }}
            </span>
          </li>
        </ul>
      </div>

    </div>
  </div>
</template>