<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  tables: { type: Array, default: () => [] },
  tableId: { type: [Number, null], default: null },
  pax: { type: Number, default: 1 },
  courseOptions: { type: Array, default: () => [] },
  customerName: { type: String, default: '' },
  /* ▼ 追加：インライン検索の結果／状態を親から受け取る */
  customerResults: { type: Array, default: () => [] },
  customerSearching: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:tableId','update:pax','chooseCourse','clearCustomer',
  'searchCustomer','pickCustomer', 'save'
])

/* 安全化 */
const safeTables  = computed(() =>
  Array.isArray(props.tables) ? props.tables.filter(t => t && t.id != null) : []
)
const safeCourses = computed(() =>
  Array.isArray(props.courseOptions) ? props.courseOptions.filter(c => c && c.id != null) : []
)

/* セットは選択→即 emit → クリア */
const selectedCourseId = ref(null)
watch(selectedCourseId, (id) => {
  if (id == null) return
  const opt = safeCourses.value.find(c => c.id === id)
  if (opt) emit('chooseCourse', opt)
})

/* 検索クエリ（ローカル） */
const q = ref('')
const doSearch = () => emit('searchCustomer', q.value.trim())
</script>

<template>
  <div class="panel base">
    <div class="wrap d-flex flex-column gap-5 w-100">
      <!-- テーブル -->
      <div class="box">
        <div class="title"><IconPinned /> テーブル</div>
        <select class="form-select" :value="tableId" @change="e => emit('update:tableId', e.target.value ? Number(e.target.value) : null)">
          <option :value="null">-</option>
          <option v-for="t in safeTables" :key="t.id" :value="t.id">
            {{ t.number }}
          </option>
        </select>
      </div>

      <!-- 人数 -->
      <div class="box">
        <div class="title"><IconUsers /> 人数</div>
        <select class="form-select" :value="pax" @change="e => emit('update:pax', Number(e.target.value))">
          <option v-for="n in 12" :key="n" :value="n">{{ n }}</option>
        </select>
      </div>

      <!-- セット -->
      <div class="box">
        <div class="title"><IconHistoryToggle /> セット</div>
        <select v-model="selectedCourseId" class="form-select">
          <option :value="null">- SET -</option>
          <option v-for="c in safeCourses" :key="c.id" :value="c.id">
            {{ c.label }}
          </option>
        </select>
      </div>

      <!-- 顧客 -->
      <div class="box">
        <div class="title"><IconUserScan /> 顧客</div>
        <div class="d-flex align-items-center gap-2">
          <div class="form-control bg-light position-relative">
            {{ customerName || '未選択' }}
            <div class="button-area position-absolute">
              <button class="" @click="doSearch"><IconSearch :size="16" /></button>
              <button class="" :disabled="!customerName" @click="emit('clearCustomer')"><IconX :size="16"/></button>
            </div>
          </div>

        </div>



        <!-- 検索入力 -->
        <div style="margin-top:8px;">
          <input class="form-control" type="text" v-model="q" placeholder="名前／TEL などで検索" @keyup.enter="doSearch">
        </div>

        <!-- ▼ 検索結果（下にズラッと） -->
        <div v-if="customerSearching" class="small text-muted" style="margin-top:6px;">検索中…</div>
        <ul v-if="customerResults && customerResults.length" style="margin-top:8px; padding-left:0; list-style:none;">
          <li v-for="(c,i) in customerResults" :key="c?.id ?? i" style="display:flex; align-items:center; gap:8px; padding:6px 0; border-top:1px solid #eee;">
            <div class="flex-grow-1">
              <div class="fw-bold">{{ c.alias || c.full_name || ('#'+c.id) }}</div>
              <div class="small text-muted">{{ c.phone || c.email || '' }}</div>
            </div>
            <button class="btn btn-sm btn-primary" @click="emit('pickCustomer', c)">選択</button>
          </li>
        </ul>
        <div v-else-if="q" class="small text-muted" style="margin-top:6px;">検索結果なし</div>
      </div>
    </div>
    <div class="savebutton">
      <button class="btn btn-primary w-100 mt-5" @click="$emit('save')">保存</button>
    </div>
  </div>
</template>
