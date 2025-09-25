<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { setBillDiscountByCode,updateBillDiscountRule,fetchDiscountRules,fetchBasicDiscountRules } from '@/api'

const props = defineProps({
  tables: { type: Array, default: () => [] },
  tableId: { type: [Number, null], default: null },
  pax: { type: Number, default: 1 },
  courseOptions: { type: Array, default: () => [] },
  customerName: { type: String, default: '' },
  customerResults: { type: Array, default: () => [] },
  customerSearching: { type: Boolean, default: false },

  seatTypeOptions: { type: Array, default: () => [
    { code:'main', label:'メイン' },
    { code:'counter', label:'カウンター' },
    { code:'box', label:'ボックス' },
  ] },
  seatType: { type: String, default: 'main' },

  /* SET（60分固定） */
  male:   { type: Number, default: 0 },
  female: { type: Number, default: 0 },
  night:  { type: Boolean, default: false },
  special:{ type: String,  default: 'none' },
})

const emit = defineEmits([
  'update:seatType','update:tableId','update:pax',
  'chooseCourse','clearCustomer','searchCustomer','pickCustomer',
  'applySet','save'
])


/* 数量ステッパー（男性・女性共通） */
function qtyOf(kind){
  return kind === 'male' ? Number(maleRef.value)||0 : Number(femaleRef.value)||0
}
function inc(kind){
  if (kind === 'male') maleRef.value   = qtyOf('male')   + 1
  else                femaleRef.value = qtyOf('female') + 1
}
function dec(kind){
  if (kind === 'male') maleRef.value   = Math.max(0, qtyOf('male')   - 1)
  else                femaleRef.value = Math.max(0, qtyOf('female') - 1)
}

/* 内部表示用（props同期のみ） */
const q = ref('') 
const seatTypeRef = ref(props.seatType || 'main')
watch(() => props.seatType, v => { seatTypeRef.value = v || 'main' })

/* 席種候補の自動抽出 */
const seatTypeOptionsAuto = computed(() => {
  const set = new Map()
  for (const t of (props.tables || [])) {
    const code = (t?.seat_type || 'main') + ''
    if (!set.has(code)) set.set(code, { code, label: code==='main'?'メイン': code==='counter'?'カウンター': code==='box'?'ボックス': code })
  }
  const fromProps = (props.seatTypeOptions || []).filter(o => o?.code)
  return fromProps.length ? fromProps : Array.from(set.values())
})

/* 席種変更をemit専用で処理（テンプレで .value を触らない） */
function onSeatTypeInput (e) {
  const v = e?.target?.value ?? 'main'
  emit('update:seatType', v)
}

/* 席種でテーブルを絞る */
const safeTables = computed(() => Array.isArray(props.tables) ? props.tables.filter(t => t && t.id!=null) : [])
const filteredTables = computed(() => {
  const code = seatTypeRef.value
  const src = safeTables.value
  if (!src.length) return []
  if (src[0]?.seat_type == null) return src
  return src.filter(t => String(t.seat_type) === String(code))
})

/* SET（60分固定） */
const maleRef    = ref(props.male)
const femaleRef  = ref(props.female)
const nightRef   = ref(props.night)
const specialRef = ref(props.special)
watch(() => props.male,   v => maleRef.value   = v)
watch(() => props.female, v => femaleRef.value = v)

// ★ 割引ルール（APIから動的取得）
const discountRules = ref([{ code: 'none', name: '通常' }])
onMounted(async () => {
try {
  const arr = await fetchBasicDiscountRules()
  const list = arr
    .filter(r => r && r.code && r.name)
    .map(r => ({ code: String(r.code), name: String(r.name) }))
  discountRules.value = [{ code:'none', name:'通常' }, ...list]
  // 既定値がAPIに無い場合のガード
  if (!discountRules.value.some(r => r.code === specialRef.value)) {
    specialRef.value = 'none'
  }
} catch (e) {
  console.warn('[discount-rules] load failed:', e?.message)
  discountRules.value = [{ code:'none', name:'通常' }]
  specialRef.value = 'none'
}
})

function applySet(){
  const m = Number(maleRef.value||0)
  const f = Number(femaleRef.value||0)
  if (m + f <= 0) { alert('SETの人数を入力してください'); return }
  emit('applySet', {
    // ラインは SET と 深夜のみ（クーポン行は追加しない）
    lines: [
      { type:'set',   code:'setMale',   qty:m },
      { type:'set',   code:'setFemale', qty:f },
      ...(nightRef.value ? [{ type:'addon',  code:'addonNight', qty:(m+f) }] : []),
    ],
    // 表示用の補足（任意）
    config: { night: !!nightRef.value },
    // ★ 割引は DiscountRule に一本化：選択コードを親へ渡す
    discount_code: (specialRef.value !== 'none') ? String(specialRef.value) : null,
  })
}
</script>

<template>
  <div class="panel base">
    <div class="wrap d-flex flex-column gap-3 w-100">

      <!-- 席種 -->
      <div class="box">
        <div class="title"><IconCategory2 /> 席種</div>
        <div class="btn-group w-100">
          <template v-for="opt in seatTypeOptionsAuto" :key="opt.code">
            <input
              type="radio" class="btn-check" :id="`st-${opt.code}`"
              :value="opt.code" :checked="opt.code===seatTypeRef"
              @change="onSeatTypeInput" />   <!-- ★ emit専用関数 -->
            <label class="btn btn-outline-secondary btn-sm" :for="`st-${opt.code}`">{{ opt.label }}</label>
          </template>
        </div>
      </div>

      <!-- テーブル -->
      <div class="box">
        <div class="title"><IconPinned /> テーブル</div>
        <select class="form-select" :value="tableId"
                @change="e => $emit('update:tableId', e.target.value ? Number(e.target.value) : null)">
          <option :value="null">-</option>
          <option v-for="t in filteredTables" :key="t.id" :value="t.id">{{ t.number }}</option>
        </select>
      </div>

      <!-- SET（60分固定：男・女・深夜・特例） -->
      <div class="box">
        <div class="title"><IconSettings2 /> セット（60分）</div>

        <div class="mb-3">

          <div class="d-flex align-items-center justify-content-between gap-3">

            <!-- 男性 -->
            <div class="d-flex align-items-center">
              <IconGenderMale class="text-info" stroke-width="1.5"/>
              <!-- 数量ステッパー -->
              <div class="cartbutton d-flex align-items-center">
                <div class="d-flex align-items-center gap-3 bg-light h-auto p-2 m-2" style="border-radius:100px;">
                  <button type="button"
                          @click="dec('male')"
                          :class="{ invisible: qtyOf('male') === 0 }">
                    <IconMinus :size="16" />
                  </button>
                  <span>{{ qtyOf('male') }}</span>
                  <button type="button" @click="inc('male')">
                    <IconPlus :size="16" />
                  </button>
                </div>
              </div>
            </div>
            <!-- 女性 -->
            <div class="d-flex align-items-center">
              <IconGenderFemale class="text-danger" stroke-width="1.5"/>
              <div class="d-flex align-items-center">
                <!-- 数量ステッパー -->
                <div class="cartbutton d-flex align-items-center">
                  <div class="d-flex align-items-center gap-3 bg-light h-auto p-2 m-2" style="border-radius:100px;">
                    <button type="button"
                            @click="dec('female')"
                            :class="{ invisible: qtyOf('female') === 0 }">
                      <IconMinus :size="16" />
                    </button>
                    <span>{{ qtyOf('female') }}</span>
                    <button type="button" @click="inc('female')">
                      <IconPlus :size="16" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

          </div>

        </div>

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
                <input class="btn-check"
                      type="radio"
                      name="sp"
                      :id="`sp-${r.code}`"
                      :value="r.code"
                      v-model="specialRef">
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

      <!-- 顧客（既存） -->
      <div class="box">
        <div class="title"><IconUserScan /> 顧客</div>
        <div class="form-control bg-light position-relative">
          {{ customerName || '未選択' }}
          <div class="button-area position-absolute">
            <button class="" @click="() => emit('searchCustomer', q.value)"><IconSearch :size="16" /></button>
            <button class="" :disabled="!customerName" @click="$emit('clearCustomer')"><IconX :size="16"/></button>
          </div>
        </div>
        <div class="mt-2">
          <input class="form-control" type="text" v-model="q" placeholder="名前／TEL などで検索" @keyup.enter="() => emit('searchCustomer', q.value)">
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
