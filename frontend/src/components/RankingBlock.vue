<!-- src/components/RankingBlock.vue -->
<script setup>
import { computed } from 'vue'
import { yen } from '@/utils/money'

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

// ★ メダル SVG の絶対パスを返すヘルパ
const medalSrc = i => `/img/rank-no${i + 1}.svg`
</script>

<template>
  <div class="ranking-block">
    <h5>{{ label }}</h5>

    <!-- ─── 1-3 位 ─────────────────────── -->
    <div class="top-three d-flex" v-if="topThree.length">
      <div
        v-for="(r,i) in topThree"
        :key="r.cast_id"
        class="number d-flex flex-column align-items-center justify-content-end gap-3"
        :class="'no'+(i+1)"
      >
        <div class="avatar">
          <img v-if="r.avatar_url" :src="r.avatar_url" />
        </div>
		<div class="wrap d-flex gap-3 align-items-center">
			<!-- ★ ここで順位ごとの SVG を差し替え -->
			<img :src="medalSrc(i)" :alt="`No.${i+1}`" class="medal" />
			<div class="content">
				<div class="name">{{ r.stage_name }}</div>
				<span class="fw-bold">{{ yen(r.revenue) }}</span>
			</div>
		</div>

      </div>
    </div>

    <!-- ─── 4 位以下 ─────────────────────── -->
    <div v-if="others.length" class="others px-4 py-2 bg-white">
      <div
        v-for="(r,i) in others"
        :key="r.cast_id"
        class="other-item d-flex align-items-center mb-2 gap-2"
      >
        <span class="rank-index">No.{{ i + 4 }}</span>
        <div class="avatar"><img v-if="r.avatar_url" :src="r.avatar_url" /></div>
        <span class="flex-grow-1">{{ r.stage_name }}</span>
        <div class="bar flex-grow-1" :style="{ width: barW(r) }"></div>
        <span class="fw-bold">{{ yen(r.revenue) }}</span>
      </div>
    </div>

    <!-- 4 位以下データ無し -->
    <div v-else class="others-empty text-muted text-center py-3">
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
