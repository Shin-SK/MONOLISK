<!-- /src/views/CastRanking.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import RankingBlock from '@/components/RankingBlock.vue'
import { fetchCastRankings } from '@/api'

const rowsGekkan = ref([])
const rowsKami   = ref([])
const rowsShimo  = ref([])

async function load () {
  const start  = dayjs().startOf('month').format('YYYY-MM-DD')
  const middle = dayjs().startOf('month').add(14, 'day').format('YYYY-MM-DD')
  const end    = dayjs().endOf('month').format('YYYY-MM-DD')

  const [gekkan, kami, shimo] = await Promise.all([
    fetchCastRankings({ from: start,  to: end }),
    fetchCastRankings({ from: start,  to: middle }),
    fetchCastRankings({ from: dayjs(middle).add(1,'day').format('YYYY-MM-DD'), to: end }),
  ])

  rowsGekkan.value = gekkan
  rowsKami.value   = kami
  rowsShimo.value  = shimo
}
onMounted(load)
</script>

<template>
  <div class="container mt-4">
    <h5 class="mt-5 text-center fw-bold"><IconCrown />月間ランキング</h5>
    <RankingBlock
      :rows="rowsGekkan"
    />
    <h5 class="mt-5 text-center fw-bold"><IconCrown />月前半ランキング</h5>
    <RankingBlock
      :rows="rowsKami"
    />
    <h5 class="mt-5 text-center fw-bold"><IconCrown />月後半ランキング</h5>
    <RankingBlock
      :rows="rowsShimo"
    />
  </div>
</template>
