<!-- src/components/RankingBlock.vue -->
<script setup>
import { computed } from 'vue'
import { yen } from '@/utils/money'
import Avatar from '@/components/Avatar.vue'

// --- props ---
const props = defineProps({
  rows : { type:Array,  required:true },
  label: { type:String, default:'' }
})

// --- データ分割 & ヘルパ ---
const topThree = computed(() => props.rows.slice(0, 3))
const others   = computed(() => props.rows.slice(3))
const max      = computed(() => props.rows[0]?.revenue || 1)
const barW     = r => `${(r.revenue / max.value * 100).toFixed(0)}%`

// ★ 各順位ごとのアバターサイズ（px）
const sizeByRank = [40, 35, 30]        // 1位,2位,3位
const avatarSize = i => sizeByRank[i]  // helper

//  メダル SVG の絶対パスを返すヘルパ
const medalSrc = i => `/img/rank-no${i + 1}.svg`

</script>

<template>
  <div class="ranking-block">
      
    
    <!-- ─── 1-3 位 ─────────────────────── -->
    <div v-if="topThree.length"
      class="bg-white p-3">

      <div v-for="(r,i) in topThree" :key="r.cast_id"
        class="number row align-items-center g-2 mb-4"
        :class="'no'+(i+1)" >

        <div class="col-2">
          <span>No.{{ i + 1 }}</span>
        </div>

        <div class="col-10 d-flex align-items-center gap-2">
          <div class="avatar df-center" :style="{ width: avatarSize(i) + 'px', height: avatarSize(i) + 'px' }">
            <Avatar :url="r.avatar_url" :size="avatarSize(i)" />
          </div>
          <div class="wrap">
            <div class="fw-bold">{{ r.stage_name }}</div>
            <span class="">{{ yen(r.revenue) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ─── 4 位以下 ─────────────────────── -->
    <div
      v-if="others.length"
      class="others"
    >
      <div
        v-for="(r,i) in others"
        :key="r.cast_id"
        class="row align-items-center g-2 "
      >
        <div class="col-2">No.{{ i + 4 }}</div>
        
        <div class="col-10">
          <div class="avatar">
            <Avatar :url="r.avatar_url" :size="40" class="rounded-circle" />
          </div>
          <div class="wrap">
            <div class="fw-bold">{{ r.stage_name }}</div>
            <span class="">{{ yen(r.revenue) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 4 位以下データ無し -->
    <div
      v-if="!topThree.length && !others.length"
      class="others-empty text-muted p-3 d-flex align-items-center justify-content-center flex-fill"
    >
      集計されていません
    </div>
  </div>
</template>

<style scoped>
/* スマホ横スクロール */
@media (max-width: 575.98px) {
  .top-three { overflow-x:auto;-webkit-overflow-scrolling:touch;scroll-snap-type:x mandatory; }
  .top-three .number { flex:0 0 auto;scroll-snap-align:center; }
}

/* メダル SVG のサイズはここで調整 */
.medal { width:64px;height:auto; }

/* 棒グラフ */
.other-item .bar { background:#e9ecef;height:8px;border-radius:4px; }
</style>
