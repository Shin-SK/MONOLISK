<!-- CastsPanel.vue（差し替え） -->
<script setup>
import { ref, computed } from 'vue'
import Avatar from '@/components/Avatar.vue'

const props = defineProps({
  currentCasts: { type: Array,  default: () => [] },
  benchCasts:   { type: Array,  default: () => [] },
  onDutyIds:    { type: Array,  default: () => [] },
  keyword:      { type: String, default: '' },
})
// 同伴イベントを追加
const emit = defineEmits(['update:keyword','setFree','setInhouse','setMain','setDohan','setHelp','removeCast','save'])

const isOnDuty = (c) => Array.isArray(props.onDutyIds) && props.onDutyIds.includes(Number(c?.id))

const safeCurrent = computed(() =>
  Array.isArray(props.currentCasts) ? props.currentCasts.filter(c => c && c.id != null) : []
)
const safeBench = computed(() =>
  (Array.isArray(props.benchCasts) ? props.benchCasts : [])
    .filter(c => c && c.id != null)
    .filter(isOnDuty)
)

// ナビゲーションタブの状態管理
const activeTab = ref('cast')  // 'cast', 'history'

// タブ切り替え（表示/非表示）
function switchTab(tabId) {
  activeTab.value = tabId
}

/* 色クラス（堅牢版）
   優先: stay_type → role/dohan/inhouse → is_honshimei/is_main
   'nom'   = 本指（赤）
   'dohan' = 同伴（グレー/黄）
   'in'    = 場内（緑）
   それ以外 = フリー（青）
*/
const tagClass = (c) => {
  // help は free 上のフラグ。見た目は“紫”を最優先で反映
  if (c?.is_help === true) return 'bg-purple text-white'
  // 1) stay_type が来ていればそれで確定
  let st = c?.stay_type
  // 2) 互換: role/dohan/inhouse から推定
  if (!st) {
    if (c?.role === 'main') st = 'nom'
    else if (c?.dohan)      st = 'dohan'
    else if (c?.inhouse)    st = 'in'
    else if (c?.is_help)    st = 'help'
  }
  // 3) さらに互換: is_honshimei / is_main 系
  if (!st) {
    if (c?.is_honshimei || c?.is_main) st = 'nom'
  }
  // 4) マッピング
  return st === 'nom'   ? 'bg-danger text-white'
       : st === 'in'    ? 'bg-success text-white'
       : st === 'dohan' ? 'bg-secondary text-white'
       : st === 'help' ? 'bg-purple text-white'
       :                  'bg-blue text-white'
}
/* フリー⇄場内トグル（本指/同伴はここでは触らない） */
function toggleFreeInhouse(c) {
  // 本指・同伴はここでは触らない
  if (c.role === 'main' || c.dohan) return

  // 現在の状態を正規化
  const st = c.stay_type ?? (c.inhouse ? 'in' : 'free')
  const help = !!c.is_help

  // 青( free, !help ) → 紫( free, help ) → 緑( in ) → 青 …
  if (st === 'in') {
    // 緑 → 青
    emit('setFree', c.id)
  } else if (st === 'free' && !help) {
    // 青 → 紫
    emit('setHelp', c.id)
  } else {
    // 紫( free+help ) → 緑
    emit('setInhouse', c.id)
  }
}

if (import.meta.env.DEV) {
  // 今出ている配列が見たい時
  window.__cur = safeCurrent
  window.__bench = safeBench
}

</script>

<template>
  <div class="panel casts">


     <nav class="row border-bottom g-1">
      <div
      class="col-6"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'cast' }">
        <button 
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="switchTab('cast')">
          キャスト配置
        </button>
      </div>
      <div
      class="col-6"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'history' }"  >
        <button 
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="switchTab('history')">
          着席履歴
        </button>
      </div>
    </nav>


    <div class="wrap mt-3 position-relative" v-show="activeTab === 'cast'" style="padding-bottom: 80px;">
      <div class="d-flex p-2 justify-content-between align-items-center">
        <span class="fw-bold">稼働中キャスト</span>
        <div class="d-flex justify-content-end align-items-center gap-1">
          <div class="badge bg-blue df-center">フリー</div>→<div class="badge bg-success df-center">場内</div>→<div class="badge bg-purple df-center">ヘルプ</div>
        </div>

      </div>
      
      <!-- スクロール可能エリア -->
      <div>
        <!-- 現在ついているキャスト -->
        <div class="now-cast mb-3 py-4">
          <div v-if="!safeCurrent.length" class="empty">未選択</div>
          <div v-else class="items">
            <div
              v-for="(c,i) in safeCurrent"
              :key="c?.id ?? i"
              class="item"
              :class="tagClass(c)"
            >
              <div class="wrap" @click="toggleFreeInhouse(c)">
                <div class="avatar">
                  <Avatar :url="c.avatar_url" :alt="c.stage_name" :size="40" class="rounded-circle" />
                </div>
                <div class="name">{{ c.stage_name }}</div>
              </div>
              <button class="text-white" @click.stop="emit('removeCast', c.id)" aria-label="remove">
                <IconX :size="16" />
              </button>
            </div>
          </div>
        </div>

        <!-- ベンチ（未選択） -->
        <div class="bench-cast mb-3">
          <div class="items">
            <div
              v-for="(c,i) in safeBench"
              :key="c?.id ?? i"
              class="item"
              :class="{ 'is-off': !isOnDuty(c) }"
            >
              <div class="wrap">
                <div class="avatar">
                  <Avatar :url="c.avatar_url" :alt="c.stage_name" :size="40" />
                </div>
                <div class="name">{{ c.stage_name }}</div>
              </div>

              <!-- 出勤外はボタン非表示 -->
              <div class="button-area" v-if="isOnDuty(c)">
                <button class="btn btn-sm btn-secondary text-white" @click="emit('setDohan', c.id)">同伴</button>
                <button class="btn btn-sm btn-danger"  @click="emit('setMain', c.id)">本指</button>
                <button class="btn btn-sm bg-blue text-white" @click="emit('setFree', c.id)">フリー</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- フッター固定ボタン（画面下部に固定） -->
      <div class="savebutton position-fixed bottom-0 start-0 end-0 p-3" style="bottom: 80px !important; z-index: 1000;">
        <button class="btn btn-primary w-100" @click="$emit('save')">保存</button>
      </div>

    </div>

      <div class="box" v-show="activeTab === 'history'">
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

</template>

<style scoped lang="scss">
.casts{
  .button-area{
    .btn{ white-space: nowrap; }
  }
}

.items .item.is-off{
  opacity: .45;
  filter: grayscale(100%);
  pointer-events: none;
  user-select: none;
}
</style>
