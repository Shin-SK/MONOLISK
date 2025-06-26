<!-- src/views/ReservationList.vue -->
<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { getStores, getCastProfiles, getReservations, deleteReservations } from '@/api'
import { useRouter } from 'vue-router'
const router = useRouter()

const stores = ref([])
const casts	= ref([])
const rows	 = ref([])
const selected = ref(new Set())

// 親から “初期フィルタ” を受け取れるように
const props = defineProps({
  initFilters: { type: Object, default: () => ({}) }
})

const form = ref({
  store:'', cast:'', date:'',
  ...props.initFilters           // ここでマージ
})

/* ─── 日付ユーティリティ ─── */
const today			= new Date()
const yyyy_mm_dd = d => d.toISOString().slice(0, 10)

function setRelative(days) {
	const d = new Date(today)
	d.setDate(d.getDate() + days)
	form.value.date = yyyy_mm_dd(d)
}
function clearDate() { form.value.date = '' }

/* date input を隠しておいて click() で開く */
const dateInput = ref(null)
function openPicker() { dateInput.value?.showPicker?.() || dateInput.value?.click() }

/* 店舗変更→キャスト候補更新（未選択なら全キャスト） */
watch(() => form.value.store, async s => {
	form.value.cast = ''
	casts.value = await getCastProfiles(s || undefined)
})

/* 検索実行 */
async function search() {
	rows.value = await getReservations({ ...form.value, ordering: '-start_at' })
}

async function resetForm() {
  form.value = { store:'', cast:'', date:'' }
  casts.value = await getCastProfiles()    // 全キャスト
  await search()
}

// 削除
function toggle(id) {
  selected.value.has(id)
    ? selected.value.delete(id)
    : selected.value.add(id)
}

const allChecked = computed({
  get: () => rows.value.length && selected.value.size === rows.value.length,
  set: (val) => {
    selected.value = val
      ? new Set(rows.value.map(r => r.id))
      : new Set()
  }
})

async function bulkDelete() {
  if (!confirm(`${selected.value.size} 件を削除します。よろしいですか？`)) return
  try {
    await deleteReservations([...selected.value])
    // 削除済みを UI から除外
    rows.value = rows.value.filter(r => !selected.value.has(r.id))
    selected.value.clear()
  } catch (e) {
    alert('削除に失敗しました')
    console.error(e)
  }
}


onMounted(async () => {
	stores.value = await getStores()
	casts.value	= await getCastProfiles()	 // 全キャスト
	search()
})
</script>



<template>
<div class="ReservationList container-md py-4">
	<h1 class="h3">予約一覧</h1>

<!-- ReservationList.vue ― 検索フォーム -->
  <div class="search">
    <form class="form search-row" @submit.prevent="search">
      <!-- 店舗ラジオ -->
      <fieldset class="field-group radio-items radio-store">
        <label class="radio-item">
          <input type="radio" value="" v-model="form.store" />
          <span>全店舗</span>
        </label>
        <label v-for="s in stores" :key="s.id" class="radio-item">
          <input type="radio" :value="s.id" v-model="form.store" />
          <span>{{ s.name }}</span>
        </label>
      </fieldset>

      <div class="search-wrap">
        <!-- キャストラジオ -->
        <fieldset class="field-group radio-cast radio-items" :disabled="!casts.length">
          <label v-for="c in casts" :key="c.id" class="radio-item">
            <input type="radio" :value="c.id" v-model="form.cast" />
            <img :src="c.photo_url" class="cast-icon" />
            <span>{{ c.stage_name }}</span>
          </label>
        </fieldset>

        <!-- 日付 -->
        <div class="field-group date-box">
          <!-- ① ショートカット -->
          <div class="button-area">
            <!-- 昨日／今日／明日ボタン -->
            <button
              type="button"
              :class="['btn btn-dark', { active: form.date === yyyy_mm_dd(new Date(today.setDate(today.getDate()-1))) }]"
              @click="setRelative(-1)"
            >昨日</button>

            <button
              type="button"
              :class="['btn btn-dark', { active: form.date === yyyy_mm_dd(new Date()) }]"
              @click="setRelative(0)"
            >今日</button>

            <button
              type="button"
              :class="['btn btn-dark', { active: form.date === yyyy_mm_dd(new Date(today.setDate(today.getDate()+1))) }]"
              @click="setRelative(1)"
            >明日</button>

            <!-- 日付指定ボタン（選択済み＝active） -->
            <button
              type="button"
              :class="['btn btn-dark', { active: form.date && !['昨日','今日','明日'].includes(form.date) }]"
              @click="openPicker"
            >日付指定</button>
              <!-- 隠れ input -->
              <input
                type="date"
                ref="dateInput"
                v-model="form.date"
                @change="$event.target.blur()"
                class="hidden-input"
              />
          </div>
          <div class="result">
              <span v-if="form.date" class="selected-date">{{ form.date }}</span>
              <button
                v-if="form.date"
                type="button"
                @click="clearDate"
              ><span class="material-symbols-outlined">close</span></button>
          </div>
        </div>
      </div>


      <!-- ボタン -->
      <div class="btn-wrap">
        <button type="submit" class="btn btn-dark btn-search">検索</button>
        <button type="button" class="btn btn-dark btn-reset" @click="resetForm">リセット</button>
        <button class="btn btn-dark btn-new" @click="router.push('/reservations/new')">
          新規予約
        </button>
      </div>

    </form>
  </div>


  <div class="list">
    <table class="table table-bordered table-hover align-middle table-striped">
      <thead class="table-dark">
        <tr>
          <th><input type="checkbox" v-model="allChecked" /></th>
          <th>ID</th>
          <th>店舗</th>
          <th>キャスト</th>
          <th>開始</th>
          <th>コース</th>
          <th>顧客</th>
          <th>コース</th>        <!-- minutes のまま → 詳細表示用へ変更 -->
          <th>オプション</th>    <!-- ★追加 -->
          <th>PU Driver</th>
          <th>DO Driver</th>
          <th>ドライバー</th>
          <th>予約金</th>
          <th>受取金</th>
          <th>入金</th>
          <th>状態</th><th>リンク</th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>
            <input
              type="checkbox"
              :checked="selected.has(r.id)"
              @change="toggle(r.id)"
            />
          </td>
          <td>{{ r.id }}</td>
          <td>{{ r.store_name }}</td>
          <td class="cast">
            <img v-for="(p,i) in r.cast_photos"
            :key="i"
            :src="p"
            class="cast-icon">
            {{ r.cast_names.join(', ') }}
          </td>
          <td>{{ new Date(r.start_at).toLocaleString() }}</td>
          <td>{{ r.course_minutes }}min</td>
          <td>{{ r.customer_name }}</td>
          <td>
            <template v-if="r.courses && r.courses.length">
              {{ r.courses.map(c => c.minutes + '分').join(', ') }}
            </template>
            <template v-else>―</template>
          </td>

          <!-- オプション列: 名前をカンマ区切りで -->
          <td>
            <template v-if="r.options && r.options.length">
              {{ r.options.map(o => o.name || '(自由課金)').join(', ') }}
            </template>
            <template v-else>―</template>
          </td>
          <td>{{ r.drivers.find(d=>d.role==='PU')?.driver_name || '―' }}</td>
          <td>{{ r.drivers.find(d=>d.role==='DO')?.driver_name || '―' }}</td>
          <td>{{ r.driver_name || '―' }}</td>
          <td class="text-end">{{ (r.expected_amount??0).toLocaleString() }}円</td>
          <td class="text-end">{{ (r.received_amount??0).toLocaleString() }}円</td>
          <td class="text-end">{{ (r.deposited_amount??0).toLocaleString() }}円</td>
          <td>{{ r.status }}</td>
          <td>
            <button class="btn btn-link p-0"
                    @click="router.push(`/reservations/${r.id}`)">
              詳細
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

    <button class="btn btn-danger mb-3" :disabled="!selected.size" @click="bulkDelete" >
      選択を削除
    </button>

</div>
</template>
