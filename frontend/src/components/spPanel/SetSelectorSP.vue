<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchMasters } from '@/api' // master一覧を使って code→id 変換するため
// billId は親側で持っているので、ここでは“何を追加するか”の仕様を emit する
const props = defineProps({
  billId: { type: Number, required: true },
})
const emit = defineEmits(['apply'])

const male = ref(0)
const female = ref(0)
const minutes = ref(60)                    // 60/90/120（必要に応じてUI拡張）
const night = ref(false)                   // 深夜 +1000/人
const selectedSet = ref('')                // 選択したSET商品ID（setMale/setFemale含む）
const special = ref('none')                // none | initial | agency | referral

// code → master 行（id/price）辞書
const masters = ref({})
onMounted(async () => {
  try {
    const list = await fetchMasters()      // 既存API（item-masters）を使用
    // SETカテゴリ（setMale/setFemale含む）だけ抽出
    const setMasters = (list || []).filter(m => m.category?.code === 'set' && m.category?.show_in_menu)
    masters.value = Object.fromEntries(
      setMasters.map(m => [String(m.id), m])
    )
  } catch (e) {
    console.warn('[SetSelectorSP] fetchMasters failed:', e?.message)
  }
})

/** 親へ “追加すべき行” を返す。実際の addBillItem は親で実施 */
function confirm() {
  const m = Number(male.value || 0)
  const f = Number(female.value || 0)
  if (!selectedSet.value) { alert('セット商品を選択してください'); return }
  if (m + f <= 0) { alert('人数を入力してください'); return }

  // 選択したSET商品（setMale/setFemale含む）を人数分追加
  const selectedMaster = masters.value[selectedSet.value]
  if (!selectedMaster) { alert('セット商品情報が取得できません'); return }
  // 男女別人数は従来通り保持
  const lines = []
  if (selectedMaster.code === 'setMale') {
    if (m > 0) lines.push({ type: 'set', master_id: selectedMaster.id, qty: m, meta: { minutes: minutes.value } })
  } else if (selectedMaster.code === 'setFemale') {
    if (f > 0) lines.push({ type: 'set', master_id: selectedMaster.id, qty: f, meta: { minutes: minutes.value } })
  } else {
    // 汎用SET（例: set_3000）は男性人数分追加（女性は割引等で別途処理）
    if (m > 0) lines.push({ type: 'set', master_id: selectedMaster.id, qty: m, meta: { minutes: minutes.value } })
  }
  // 深夜 +1000/人（任意・qtyは総人数）
  if (night.value) lines.push({ type: 'addon', code: 'addonNight', qty: (m + f), price_hint: 1000 })
  // 特例（SET専用割引）… 相互排他：noneなら無し
  if (special.value !== 'none') {
    lines.push({
      type: 'coupon',
      code: `coupon_${special.value}`,
      qty: 1,
      meta: { scope: 'SET', per_person: true }
    })
  }
  const payload = {
    billId: props.billId,
    config: {
      minutes: Number(minutes.value),
      night: !!night.value,
      special: String(special.value),
    },
    lines
  }
  emit('apply', payload)
}
</script>

<template>
  <div class="card border-0 shadow-sm">
    <div class="card-body">
      <div class="mb-3">
        <label class="form-label fw-bold">セット商品選択</label>
        <div class="d-flex gap-2 flex-wrap">
          <template v-for="m in Object.values(masters)" :key="m.id">
            <button
              class="btn btn-outline-primary"
              :class="{active: selectedSet.value === String(m.id)}"
              @click="selectedSet.value = String(m.id)"
            >
              {{ m.name }}<br>
              <span class="text-muted">{{ m.price_regular }}円/人</span>
            </button>
          </template>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label fw-bold">SET人数</label>
        <div class="d-flex gap-3">
          <div class="flex-fill">
            <div class="form-text mb-1">男性</div>
            <div class="input-group">
              <button class="btn btn-outline-secondary" @click="male=Math.max(0,male-1)">−</button>
              <input type="number" class="form-control text-center" v-model.number="male" min="0">
              <button class="btn btn-outline-secondary" @click="male++">＋</button>
            </div>
          </div>
          <div class="flex-fill">
            <div class="form-text mb-1">女性</div>
            <div class="input-group">
              <button class="btn btn-outline-secondary" @click="female=Math.max(0,female-1)">−</button>
              <input type="number" class="form-control text-center" v-model.number="female" min="0">
              <button class="btn btn-outline-secondary" @click="female++">＋</button>
            </div>
          </div>
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label fw-bold">SET時間</label>
        <div class="btn-group w-100">
          <input type="radio" class="btn-check" id="m60" value="60" v-model="minutes">
          <label class="btn btn-outline-secondary" for="m60">60分</label>
          <input type="radio" class="btn-check" id="m90" value="90" v-model="minutes">
          <label class="btn btn-outline-secondary" for="m90">90分</label>
          <input type="radio" class="btn-check" id="m120" value="120" v-model="minutes">
          <label class="btn btn-outline-secondary" for="m120">120分</label>
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label fw-bold">深夜加算</label>
        <div class="form-check form-switch">
          <input class="form-check-input" type="checkbox" id="night" v-model="night">
          <label class="form-check-label" for="night">+1,000 / 人</label>
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label fw-bold">特例（SET割引・相互排他）</label>
        <div class="d-flex gap-2 flex-wrap">
          <div class="form-check">
            <input class="form-check-input" type="radio" id="sp-none" value="none" v-model="special">
            <label class="form-check-label" for="sp-none">なし</label>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="radio" id="sp-initial" value="initial" v-model="special">
            <label class="form-check-label" for="sp-initial">初回</label>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="radio" id="sp-agency" value="agency" v-model="special">
            <label class="form-check-label" for="sp-agency">案内所</label>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="radio" id="sp-ref" value="referral" v-model="special">
            <label class="form-check-label" for="sp-ref">顧客紹介</label>
          </div>
        </div>
      </div>

      <button class="btn btn-warning w-100" @click="confirm">確定</button>
    </div>
  </div>
</template>

<style scoped>
.card-body{ padding:1rem 1.25rem; }
</style>
