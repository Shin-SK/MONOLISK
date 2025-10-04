<!-- CastsPanelSP.vue（該当箇所のみ差し替え） -->
<script setup>
import { computed } from 'vue'
import Avatar from '@/components/Avatar.vue'

const props = defineProps({
  currentCasts: { type: Array,  default: () => [] },
  benchCasts:   { type: Array,  default: () => [] },
  onDutyIds:    { type: Array,  default: () => [] },
  keyword:      { type: String, default: '' },
})
const emit = defineEmits(['update:keyword','setFree','setInhouse','setMain','removeCast', 'save'])

const safeCurrent = computed(() =>
  Array.isArray(props.currentCasts) ? props.currentCasts.filter(c => c && c.id != null) : []
)
const safeBench = computed(() =>
  (Array.isArray(props.benchCasts) ? props.benchCasts : [])
    .filter(c => c && c.id != null)
    .filter(isOnDuty)
)
// 追加：当日出勤かどうか
const isOnDuty = (c) => Array.isArray(props.onDutyIds) && props.onDutyIds.includes(Number(c?.id))


/* 色クラス（free→blue / in→success / main→danger） */
const tagClass = (c) => (c.role === 'main'
  ? 'bg-danger text-white'
  : (c.inhouse ? 'bg-success text-white' : 'bg-blue text-white'))

/* ★ フリー⇄場内トグル（本指名は無視） */
function toggleFreeInhouse(c){
  if (c.role === 'main') return
  if (c.inhouse) emit('setFree', c.id)     // 場内→フリー
  else           emit('setInhouse', c.id)  // フリー→場内
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
              <!-- アバターセット全体をタップでトグル（ボタン以外） -->
              <div class="wrap" @click="toggleFreeInhouse(c)">
                <div class="avatar">
                  <Avatar :url="c.avatar_url" :alt="c.stage_name" :size="40" class="rounded-circle" />
                </div>
                <div class="name">{{ c.stage_name }}</div>
              </div>
              <!-- 削除ボタンは stop して誤トグル防止 -->
              <button class="text-white" @click.stop="emit('removeCast', c.id)" aria-label="remove">
                <IconX :size="16" />
              </button>
            </div>
          </div>
        </div>

        <!-- ベンチ（未選択）は現状のまま -->
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

              <!-- ★ 出勤外はボタンを表示しない（=選択不可） -->
              <div class="button-area" v-if="isOnDuty(c)">
                <button class="btn btn-sm bg-blue text-white" @click="emit('setFree', c.id)">フリー</button>
                <button class="btn btn-sm btn-success" @click="emit('setInhouse', c.id)">場内</button>
                <button class="btn btn-sm btn-danger"  @click="emit('setMain', c.id)">本指</button>
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
    .btn{
      white-space: nowrap;
    }
  }
}

.items .item.is-off{
  opacity: .45;
  filter: grayscale(100%);
  pointer-events: none;       /* クリック不可（リンク/ボタン全て） */
  user-select: none;
}

</style>