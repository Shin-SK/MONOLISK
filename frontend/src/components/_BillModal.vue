<!-- src/components/BillModal.vue -->
<script setup>
import { ref, watch, computed } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import { useBills } from '@/stores/useBills'
import { fetchMasters, fetchCasts } from '@/api'

/* ───────── props & v-model ───────── */
const props  = defineProps({ modelValue:Boolean, bill:Object })
const emit   = defineEmits(['update:modelValue'])
const visible = computed({
  get: () => props.modelValue,
  set: v  => emit('update:modelValue', v)
})

/* bill を安全に参照（初期ロード対策） */
const bill = computed(() => props.bill || {
  id:'', table:{number:''}, items:[], nominated_casts:[]
})

/* ───────── キャスト関連 ───────── */
const masters = ref([])
const casts   = ref([])

/* 指名構成 */
const mainCastId   = ref('')   // 本指名（1人だけ）
const freeCastIds  = ref([])   // フリー指名（複数）
const inhouseSet   = ref(new Set()) // 場内フラグ保持

const nominationType = ref('')        // 'honshi' | 'free'
const activeTab      = computed(() =>
  nominationType.value === 'honshi' ? 'honshi' : 'free'
)
const hasChoice      = computed(() => nominatedCasts.value.length > 0)

/* nominated_casts を bill に反映 */
const nominatedCasts = computed(() => {
  const ids = new Set([ mainCastId.value, ...freeCastIds.value ])
  return [...ids].filter(Boolean)
})
watch(nominatedCasts, ids => { bill.value.nominated_casts = ids })

/* ビルごとにマスタ取得 */
watch(
  () => bill.value.id,
  async id => {
    if(!id) return
    const sid = bill.value.table.store      // ここは serializer で必ず入る
    masters.value = await fetchMasters(sid)
    casts.value   = await fetchCasts(sid)
  },
  { immediate:true }
)

/* ───────── 明細追加 ───────── */
const draft = ref({ master_id:'', qty:1, cast_id:'' })
const bills = useBills()

async function add(){
  if(!draft.value.master_id) return
  const m = masters.value.find(x => x.id === draft.value.master_id)
  await bills.addItem({
    item_master : m.id,
    name        : m.name,
    price       : m.price_regular,
    qty         : draft.value.qty,
    back_rate   : m.default_back_rate,
    served_by_cast: draft.value.cast_id || null
  })
  Object.assign(draft.value, { master_id:'', qty:1, cast_id:'' })
}
</script>

<template>
  <BaseModal v-model="visible">
    <!-- タイトル -->
    <template #title>
      <h3 class="text-center fw-bold">
        伝票 #{{ bill.id }} / 卓 {{ bill.table.number }}
      </h3>
    </template>

    <div class="modal-body">
      <div
        class="wrapper d-grid"
        style="grid-template-columns: 1fr 1fr;"
      >
        <div class="outer p-3">
          <div class="nomination mb-5">
            <div class="wrap d-flex gap-4">
              <!-- ★ボタンが押されたらprimaryになる感じに -->
              <input
                id="honshi"
                type="radio"
                class="btn-check"
              >
              <label
                for="honshi"
                class="btn btn-outline-primary flex-fill"
              >本指名あり</label>
              <input
                id="free"
                type="radio"
                class="btn-check"
              >
              <label
                for="free"
                class="btn btn-outline-primary flex-fill"
              >フリー</label>
            </div>
          </div>
          <!-- ───────── 選択結果 + 場内指定 ───────── -->
          <div class="choiced-area mb-5">
            <div class="d-flex p-3 bg-light justify-content-center gap-4">
              <!-- ★選ばれてない場合は「キャストを選択してください」を表示したい -->
              <template
                v-for="cid in nominatedCasts"
                :key="cid"
              >
                <div class="btn btn-outline-primary">
                  {{ casts.find(c => c.id === cid)?.stage_name || 'N/A' }}
                  <span
                    v-if="cid === mainCastId"
                    class="badge bg-yellow ms-1"
                  >場内</span>
                  <input
                    v-model="inhouseSet"
                    type="checkbox"
                    :value="cid"
                    class="form-check-input"
                  >
                </div>
              </template>
            </div>
          </div>
          <!-- ───────── キャスト選択 ───────── -->
          <div class="cast-area">
            <div class="d-flex tab-menu">
              <button
                class="nav-link active"
                data-bs-target="#select-honshi"
                type="button"
                role="tab"
              >
                本指名
              </button> <!-- ★上の選択で、if honshiだったら、このボタンを表示 -->
              <button
                class="nav-link"
                data-bs-target="#select-free"
                type="button"
                role="tab"
              >
                フリー
              </button>
            </div>
              
            <div class="tab-area">
              <!-- ★タブを表示させたい -->

              <!-- 本指名 -->
              <div
                id="select-honshi"
                class="area honshi-area fade show active"
              >
                <!-- ★IDでつなげる -->
                <h6 class="fw-bold">
                  本指名
                </h6>
                <div
                  class="d-flex gap-4"
                  role="group"
                >
                  <!-- ★検索欄つけたい キャストの検索欄 名前だけでいいと思う -->
                  <template
                    v-for="c in casts"
                    :key="c.id"
                  >
                    <!-- hidden ラジオ -->
                    <input
                      :id="'main-'+c.id"
                      v-model="mainCastId"
                      class="btn-check"
                      type="checkbox"
                      name="mainCast"
                      :value="c.id"
                    >

                    <!-- 見えるボタン -->
                    <label
                      class="btn"
                      :class="mainCastId === c.id ? 'btn-primary' : 'btn-outline-primary'"
                      :for="'main-'+c.id"
                    >
                      {{ c.stage_name }}
                    </label>
                  </template>
                </div>
              </div>

              <!-- フリー指名（チェックボックス複数） -->
              <div
                id="select-free"
                class="area honshi-area fade"
              >
                <!-- ★IDでつなげる -->
                <h6 class="mb-1">
                  フリー
                </h6>
                <div
                  class="d-flex gap-4"
                  role="group"
                >
                  <!-- ★検索欄つけたい キャストの検索欄 名前だけでいいと思う -->
                  <template
                    v-for="c in casts"
                    :key="c.id"
                  >
                    <!-- hidden チェックボックス -->
                    <input
                      :id="'free-'+c.id"
                      v-model="freeCastIds"
                      class="btn-check"
                      type="checkbox"
                      :value="c.id"
                    >

                    <!-- 見えるボタン -->
                    <label
                      class="btn"
                      :class="freeCastIds.includes(c.id) ? 'btn-primary' : 'btn-outline-primary'"
                      :for="'free-'+c.id"
                    >
                      {{ c.stage_name }}
                    </label>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <!-- ───────── 注文フォーム ───────── -->
          <div class="d-flex gap-2 align-items-end">
            <select
              v-model="draft.master_id"
              class="form-select form-select-sm"
            >
              <option value="">
                -- item --
              </option>
              <option
                v-for="m in masters"
                :key="m.id"
                :value="m.id"
              >
                {{ m.name }} (¥{{ m.price_regular }})
              </option>
            </select>

            <input
              v-model.number="draft.qty"
              type="number"
              class="form-control form-control-sm"
              style="width:60px"
            >

            <select
              v-model="draft.cast_id"
              class="form-select form-select-sm"
              style="width:120px"
            >
              <option value="">
                -CAST-
              </option>
              <option
                v-for="c in casts"
                :key="c.id"
                :value="c.id"
              >
                {{ c.stage_name }}
              </option>
            </select>

            <button
              class="btn btn-sm btn-primary"
              @click="add"
            >
              追加
            </button>
          </div>
        </div><!-- /outer -->
        <div class="outer p-3">
          <!-- ───────── 明細テーブル ───────── -->
          <h3>注文一覧</h3>
          <table class="table table-sm mb-3">
            <thead>
              <tr><th>品名</th><th>個数</th><th>注文キャスト</th><th>単価</th></tr>
            </thead>
            <tbody>
              <tr
                v-for="it in bill.items"
                :key="it.id"
              >
                <td>{{ it.name }}</td>
                <td>{{ it.qty }}</td>
                <td>{{ it.served_by_cast_name || '-' }}</td>
                <td>{{ it.subtotal.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div><!-- /outer -->
      </div>
    </div>

    <!-- フッター -->
    <template #footer>
      <button
        class="btn btn-outline-success"
        :disabled="bill.closed_at"
        @click="bills.closeCurrent()"
      >
        締める
      </button>
    </template>
  </BaseModal>
</template>
