<!-- src/components/BasicsPanel.vue -->
<script setup>
import { ref, watch, reactive } from 'vue'

const props = defineProps({
  /** 表示切替: 'base' / 'customer'（SP用） */
  activePane: { type: String, default: 'base' },

  /** テーブル候補・現在値 */
  tables: { type: Array, default: () => [] },
  tableId: { type: [Number, null], default: null },

  /** 人数 */
  pax: { type: Number, default: 1 },

  /** セット候補（{ id, code, label } の配列） */
  courseOptions: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:tableId', 'update:pax', 'chooseCourse'])

/* ── SETをオーダーパネル風に：各コースごとの数量管理 ───────────── */
const qtyMap = reactive({}) // { [id]: qty }
const keyOf  = (id) => String(id)
const qtyOf  = (id) => qtyMap[keyOf(id)] ?? 0
const inc    = (id) => qtyMap[keyOf(id)] = qtyOf(id) + 1
const dec    = (id) => qtyMap[keyOf(id)] = Math.max(0, qtyOf(id) - 1)
const add    = (course) => {
	const q = qtyOf(course.id)
	if (q <= 0) return
	// 既存の親ハンドラ互換：q回 emit（payloadは従来通り course オブジェクト）
	for (let i = 0; i < q; i++) emit('chooseCourse', course)
	qtyMap[keyOf(course.id)] = 0
}

/* セット選択は変更時に即 choose → 自動クリア */
const selectedCourse = ref(null)
watch(selectedCourse, (opt) => {
  if (!opt) return
  emit('chooseCourse', opt)
  selectedCourse.value = null
})
</script>

<template>
  <div
    class="basics-panel d-flex gap-5 flex-md-column flex-row"
    :class="{ 'd-none d-md-block': activePane !== 'base' }"
  >
    <!-- テーブル番号 -->
    <div class="wrap">
      <div class="title mb-2"><IconPinned />テーブル</div>
      <div class="items">
        <select
          class="form-select w-100"
          :value="tableId"
          @change="e => emit('update:tableId', e.target.value ? Number(e.target.value) : null)"
        >
          <option class="text-center" :value="null">-</option>
          <option
            v-for="t in tables"
            :key="t.id"
            :value="t.id"
          >
            {{ t.number }}
          </option>
        </select>
      </div>
    </div>

    <!-- 人数 -->
    <div class="wrap">
      <div class="title mb-2"><IconUsers />人数</div>
      <div class="items">
        <select
          class="form-select w-100"
          style="width: 80px;"
          :value="pax"
          @change="e => emit('update:pax', Number(e.target.value))"
        >
          <option v-for="n in 12" :key="n" :value="n">{{ n }}</option>
        </select>
      </div>
    </div>

    <!-- セット（選択→即追加→クリア） -->
	<!-- セット：オーダーパネル準拠（名称 + 数量ステッパー + 追加◯） -->
		<div class="wrap">
			<div class="title mb-2"><IconHistoryToggle />セット</div>
			<div class="items">
				<div class="order-list d-flex flex-column gap-2">
					<div
						v-for="c in courseOptions"
						:key="c.id"
						class="d-flex p-2 bg-light w-100 rounded justify-content-between"
					>
						<!-- 左：セット名 -->
						<div class="item-area d-flex align-items-center ms-2">
							<div class="name fw-bold">
								{{ c.label }}
							</div>
						</div>

						<!-- 右：数量ステッパー & 追加 -->
						<div class="d-flex align-items-center">
							<div class="cartbutton d-flex align-items-center">
								<div
									class="d-flex align-items-center gap-3 bg-white h-auto p-2 m-2"
									style="border-radius:100px;"
								>
									<button type="button" @click="dec(c.id)" :class="{ invisible: qtyOf(c.id) === 0 }">
										<IconMinus :size="16" />
									</button>
									<span>{{ qtyOf(c.id) }}</span>
									<button type="button" @click="inc(c.id)">
										<IconPlus :size="16" />
									</button>
								</div>
							</div>
							<div class="addbutton d-flex align-items-center">
								<button type="button" @click="add(c)">
									<IconCirclePlus />
								</button>
							</div>
						</div>
					</div> <!-- /card -->
				</div> <!-- /order-list -->
			</div>
    </div>
  </div>
</template>

<style scoped>
.invisible {
  visibility: hidden;
  width: 0px;
  padding: 0px 4px;
}
.wrap { margin-bottom: .5rem; }
.title { font-weight: 600; display: flex; align-items: center; gap: .4rem; }
.items { margin-top: .25rem; }
</style>
