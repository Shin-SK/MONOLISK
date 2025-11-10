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
const special = ref('none')                // none | initial | agency | referral

// code → master 行（id/price）辞書
const masters = ref({})
onMounted(async () => {
  try {
    const list = await fetchMasters()      // 既存API（item-masters）を使用
    masters.value = Object.fromEntries(
      (list || []).map(m => [String(m.code || '').toLowerCase(), m])
    )
  } catch (e) {
    console.warn('[SetSelectorSP] fetchMasters failed:', e?.message)
  }
})

/** 親へ “追加すべき行” を返す。実際の addBillItem は親で実施 */
function confirm() {
  const m = Number(male.value || 0)
  const f = Number(female.value || 0)
  if (m + f <= 0) { alert('人数を入力してください'); return }

  // “SET（男女別）／深夜／特例クーポン” を構造化して親へ返す
  // 実際のコード→master_id 解決は parent（orここでmastersを使ってもOK）
  const payload = {
    billId: props.billId,
    config: {
      minutes: Number(minutes.value),
      night: !!night.value,                // 深夜トグル
      special: String(special.value),      // none|initial|agency|referral
    },
    lines: [
      // SET（男女別）… qty=人数
      { type: 'set', code: 'setMale',   qty: m, meta: { minutes: minutes.value } },
      { type: 'set', code: 'setFemale', qty: f, meta: { minutes: minutes.value } },
      // 深夜 +1000/人（任意・qtyは総人数）
      ...(night.value ? [{ type: 'addon', code: 'addonNight', qty: (m + f), price_hint: 1000 }] : []),
      // 特例（SET専用割引）… 相互排他：noneなら無し
      ...(special.value !== 'none' ? [{
        type: 'coupon',
        code: `coupon_${special.value}`,   // coupon_initial など（親でcode→id解決）
        qty: 1,
        // クーポン詳細は店ごとに異なるため、ここでは “SET割引” であることだけ伝える
        meta: { scope: 'SET', per_person: true }
      }] : []),
    ]
  }

  emit('apply', payload)
}
</script>

<template>
  <div class="card border-0 shadow-sm">
    <div class="card-body">
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
