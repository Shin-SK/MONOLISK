<!-- src/components/CastTableDnD.vue -->
<script setup>
import { ref, reactive, watch, computed } from 'vue'
import draggable  from 'vuedraggable'
import Avatar     from '@/components/Avatar.vue'
import dayjs from 'dayjs'

const props = defineProps({
  title      : String,
  billId     : { type: [Number, null], default: null },
  tableId    : { type: [Number, null], default: null },
  casts: { type: Array, default: () => [] },
  remainMin  : { type: [Number, null], default: null },
  pax        : { type: [Number, null], default: null },
  benchArea : { type:Boolean, default:false },
  subtotal   : { type: [Number, null], default: null },
})
const kinds = ['free', 'in', 'nom']
const emit = defineEmits(['update-stay', 'toggle-stay'])


const tableLabel = computed(() => {
	if (props.title && String(props.title).trim() !== '') return props.title
	if (props.tableId != null) return `テーブル ${props.tableId}`
	return 'テーブル'
})


/* --- Draggable 用ローカル配列 --- */
const localCasts = ref([...props.casts])

watch(() => props.casts, (newVal) => {
  localCasts.value = [...newVal]          // ベンチ列も含め常に同期
})

/*  1 分おきに強制再描画用 tick */
const tick = ref(Date.now())
setInterval(() => (tick.value = Date.now()), 60_000)

/* 色判定 util ------------- */
function bgColor(el){
  /* ベンチ列なら一律 primary */
  if (props.benchArea) return 'primary'

  if (el.kind === 'free'){
    const mins = dayjs(tick.value).diff(dayjs(el.entered_at),'minute')
    return mins >=30 ? 'orange'
         : mins >=20 ? 'orange'
         : mins >=10 ? 'warning'
         : 'blue'
  }
  return el.kind === 'nom' ? 'danger' : 'success'
}
function afterWidth(el){
  if (props.benchArea || el.kind !== 'free') return null
  const mins   = dayjs(tick.value).diff(dayjs(el.entered_at),'minute')
  const within = mins % 10
  return `${Math.min(within+1,10)*10}%`
}

/* ---------- DnD オプション ---------- */
const dragOptions = {
  swap: true,            // ← Swap プラグインを有効化
  swapThreshold: 0.7,    // 70% 以上重なったら１回だけ swap
  invertSwap: true,      // 指を戻したときに元へ戻るアニメも滑らか
  animation: 300,        // swap が確定した後の補間速度
  ghostClass: 'ghost',
  chosenClass: 'chosen',
}


function remove(el){
  emit('update-stay',{
    castId      : el.id,
    fromBillId  : props.billId  ?? null,
    toBillId    : null,                // ベンチへ
    fromTableId : props.tableId ?? null,
    toTableId   : null
  })
}

function toggleKind(el){
  /* ベンチ列はスキップ */
  if (props.benchArea || !props.billId) return

  /* 次の kind を算出 */
  const idx  = kinds.indexOf(el.kind)
  el.kind    = kinds[(idx + 1) % kinds.length]   // ローカル即時更新

  emit('toggle-stay', {            // 親に通知
    castId      : el.id,
    billId      : props.billId,
    nextKind    : el.kind
  })
}

/* ---------- ドロップ確定 ---------- */
function onDragEnd (evt) {
  /* ────────────────
   * 並び順だけが変わったケースでも
   * サーバに最新 state を送るため **必ず emit** する
   * ──────────────── */

  // ── DOM の data-id 属性からキャスト ID を得る ──
  const castId = Number(evt.item.dataset.id)
  if (!castId) return     

  const payload = {
    castId,
    fromBillId:  evt.from.dataset.billId  ? Number(evt.from.dataset.billId)  : null,
    toBillId:    evt.to.dataset.billId    ? Number(evt.to.dataset.billId)    : null,
    fromTableId: evt.from.dataset.tableId ? Number(evt.from.dataset.tableId) : null,
    toTableId:   evt.to.dataset.tableId   ? Number(evt.to.dataset.tableId)   : null
  }
  /* アニメーションが終わるタイミングで送る */
  setTimeout(() => emit('update-stay', payload), dragOptions.animation)
}

const isVacant = computed(() => !props.billId && !props.benchArea)
const showDetail = computed(() => !isVacant.value)
</script>

<template>
  <div class="table-wrap">
    <!-- ── ヘッダー ── -->
    <h5
      v-if="!benchArea"
      class="header p-2 bg-dark text-light d-flex align-items-center justify-content-between m-0 d-md-flex d-none"
    >
      <div class="table-number fs-3 d-flex align-items-center gap-1">
        <IconPinned class="mt-1" />
        <span>{{ title }}</span>
      </div>
      <div class="other-info d-flex gap-3 px-3">
        <div
          v-if="billId"
          class="item"
        >
          <IconNotes />#{{ billId }}
        </div>
        <div
          v-if="pax !== null"
          class="item"
        >
          <IconUsers />{{ pax }}
        </div>
      </div>
    </h5>

    <!-- ── 本体 ── -->
    <div class="table-box h-100 d-flex flex-column bg-white">
      <!-- 空席ラベル -->
      <div
        v-if="isVacant"
        class="vacant-label flex-grow-1 d-flex justify-content-center align-items-center fs-3 bg-secondary text-light"
        style="min-height: 100px;"
      >
        <div class="d-flex align-items-center gap-2">
          <IconPinned :size="22" />
          <span class="fw-bold">{{ tableLabel }}</span>
        </div>
      </div>
      <!-- キャスト一覧 (詳細) -->
      <draggable
        v-if="showDetail"
        v-model="localCasts"
        item-key="id"
        :group="{ name:'casts' }"
        :class="['casts bg-white d-flex flex-wrap gap-2', 
                benchArea ? 'bench-zone p-0' : 'p-3']"
        :data-bill-id="billId"
        :data-table-id="tableId"
        v-bind="dragOptions"
        @end="onDragEnd"
        @move="evt => evt.related.style.transition = 'transform .3s ease'"
      >
        <template #item="{ element }">
          <div
            class="cast-card btn text-light p-2 d-flex align-items-center"
            :class="`bg-${bgColor(element)}`"
            :style="afterWidth(element) ? {'--after-width': afterWidth(element)} : {}"
            :data-id="element.id"
            :data-bill-id="billId"
            @click.stop="toggleKind(element)"
          >
            <Avatar
              :url="element.avatar"
              :alt="element.name"
              :size="40"
              class="me-1 rounded-circle"
            />
            {{ element.name }}
          </div>
        </template>
      </draggable>
    </div>

    <!-- フッター -->
    <div
      v-if="showDetail && !benchArea"
      class="table-view-footer bg-white p-2 d-flex gap-3 justify-content-between align-items-center"
    >
      <!-- デバイス用 -->
      <div class="table-number align-items-center gap-1 d-md-none d-flex">
        <IconPinned :size="20"/>
        <span>{{ title }}</span>
      </div>

      <!-- デバイス用 -->
      <div
        v-if="billId"
        class="item d-flex gap-1 align-items-center d-md-none d-flex"
      >
        <IconNotes :size="20"/>
        <span>{{ billId }}</span>
      </div>

      <!-- デバイス系 -->
      <div
        v-if="pax !== null"
        class="item d-md-none d-flex"
      >
        <IconUsers />{{ pax }}
      </div>

      <div
        v-if="remainMin !== null"
        class="item d-flex gap-2 align-items-center"
      >
        <IconHistoryToggle :size="20"/><span>{{ remainMin }}分</span>
      </div>

      <div
        v-if="subtotal !== null"
        class="item d-flex gap-0 align-items-center"
      >
        <IconCurrencyYen :size="20"/>
        <span class="d-flex align-items-center">
          {{ subtotal.toLocaleString() }}
        </span>
      </div>

    </div>
  </div>
</template>


<style scoped>

/* ───── DnD 演出 ───── */
.chosen,
.dragging   { opacity: 0.5; }
.ghost      { opacity: 0.35; }



.cast-card{ 
  cursor:grab; 
  position:relative; 
  transition: transform .3s ease ;
}
.cast-card::after{
  content:''; 
  position:absolute; 
  left:0; 
  bottom:2px;
  height:2px;
   width:var(--after-width,0);
  background:currentColor; 
  transition:width .2s linear;
}

.cast-card {
  transition: top .25s ease, left .25s ease; /* transform ではなく top/left */
}

.fallback { opacity: .5; }    /* 掴んだ要素の半透明 */

.close-btn{ 
  position:absolute; 
  top:-4px; 
  right:-4px; 
  opacity:.8; }

.bench-zone{
  min-width: 100%;        /* ベンチ列全体がドロップエリアになる */
}
.vacant-label{
  opacity:.7;           /* うっすら表示で “空席感” */
}
</style>
