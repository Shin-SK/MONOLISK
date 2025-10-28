<!-- CastsPanelSP.vue（差し替え） -->
<script setup>
import { computed } from 'vue'
import Avatar from '@/components/Avatar.vue'

const props = defineProps({
  currentCasts: { type: Array,  default: () => [] },
  benchCasts:   { type: Array,  default: () => [] },
  onDutyIds:    { type: Array,  default: () => [] },
  keyword:      { type: String, default: '' },
})
// 同伴イベントを追加
const emit = defineEmits(['update:keyword','setFree','setInhouse','setMain','setDohan','removeCast','save'])

const isOnDuty = (c) => Array.isArray(props.onDutyIds) && props.onDutyIds.includes(Number(c?.id))

const safeCurrent = computed(() =>
  Array.isArray(props.currentCasts) ? props.currentCasts.filter(c => c && c.id != null) : []
)
const safeBench = computed(() =>
  (Array.isArray(props.benchCasts) ? props.benchCasts : [])
    .filter(c => c && c.id != null)
    .filter(isOnDuty)
)

/* 色クラス（堅牢版）
   優先: stay_type → role/dohan/inhouse → is_honshimei/is_main
   'nom'   = 本指（赤）
   'dohan' = 同伴（グレー/黄）
   'in'    = 場内（緑）
   それ以外 = フリー（青）
*/
const tagClass = (c) => {
  // 1) stay_type が来ていればそれで確定
  let st = c?.stay_type
  // 2) 互換: role/dohan/inhouse から推定
  if (!st) {
    if (c?.role === 'main') st = 'nom'
    else if (c?.dohan)      st = 'dohan'
    else if (c?.inhouse)    st = 'in'
  }
  // 3) さらに互換: is_honshimei / is_main 系
  if (!st) {
    if (c?.is_honshimei || c?.is_main) st = 'nom'
  }
  // 4) マッピング
  return st === 'nom'   ? 'bg-danger text-white'
       : st === 'in'    ? 'bg-success text-white'
       : st === 'dohan' ? 'bg-secondary text-white'
       :                  'bg-blue text-white'
}
/* フリー⇄場内トグル（本指/同伴はここでは触らない） */
function toggleFreeInhouse(c){
  if (c.role === 'main' || c.dohan) return
  if (c.inhouse) emit('setFree', c.id)
  else           emit('setInhouse', c.id)
}

if (import.meta.env.DEV) {
  // 今出ている配列が見たい時
  window.__cur = safeCurrent
  window.__bench = safeBench
}

</script>

<template>
  <div class="panel casts">
    <div class="wrap">
      <!-- 現在ついているキャスト -->
      <div class="now-cast">
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
            </button><!-- ★ ここに出てこない。bill内には入ってる-->
          </div>
        </div>
      </div>

      <!-- ベンチ（未選択） -->
      <div class="bench-cast">
        <div class="search">
          <input
            type="text"
            class="form-control"
            :value="keyword"
            @input="e => emit('update:keyword', e.target.value)"
          >
          <IconSearch :size="16" class="icon"/>
        </div>

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
              <button class="btn btn-sm btn-success" @click="emit('setInhouse', c.id)">場内</button>
              <button class="btn btn-sm bg-blue text-white" @click="emit('setFree', c.id)">フリー</button>
            </div>
          </div>
        </div>

      </div>
    </div>

    <div class="savebutton mt-5">
      <button class="btn btn-primary w-100" @click="$emit('save')">保存</button>
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
