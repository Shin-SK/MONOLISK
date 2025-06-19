<!-- src/components/TaskListView.vue -->
<script setup>
import { ref, reactive, watch, onMounted, nextTick, computed } from 'vue'
import dayjs	from 'dayjs'
import { api }	from '@/api'
import 'dayjs/locale/ja'   // 追加
import { useRouter } from 'vue-router'   // 追加


dayjs.locale('ja')         // アプリ起動時にどこかで 1 回だけ


/* ---------- props ---------- */
const props = defineProps({
  apiPath:      { type:String, required:true },   // 例 'reservations/mine-driver/'
  detailRoute:  { type:String, required:true },   // 例 '/driver/reservations'
  showSettled:  { type:Boolean, default:false },  // Driver だけ true
  selectedDate: Object                            // 既存
})

/* ---------- state ---------- */
const items          = reactive([])   // 予約リスト
const loadingPast    = ref(false)
const loadingFuture  = ref(false)
const error          = ref(null)

const router  = useRouter() // ← ここ 1 回だけ
const listRef = ref(null)

/* ---------- Pull-to-Refresh 用 ---------- */
const pullDistance = ref(0)
const isPulling    = ref(false)

/* ---------- 日付レンジ ---------- */
const today  = dayjs().startOf('day')
let oldest   = today.clone()				// 最古
let newest   = today.clone().add(3,'day')	// 未来＋3日

const rangeParams = (f,t)=>({
	from:f.format('YYYY-MM-DD'),
	to:  t.format('YYYY-MM-DD')
})


/* ---------- API ---------- */
async function fetchRange(fromDate, toDate, prepend = false) {
  try {
    const { data } = await api.get(props.apiPath, {
      params: {
        from: fromDate.format('YYYY-MM-DD'),
        to:   toDate.format('YYYY-MM-DD')
      }
    })

    const normalized = data
      .slice()
      .sort((a, b) => new Date(a.start_at) - new Date(b.start_at))

    const seen = new Set(items.map(i => i.id))

    /* 追加位置の違い（prepend / append） */
    if (prepend) {
      const beforeH = listRef.value.scrollHeight
      const beforeT = listRef.value.scrollTop

      normalized.slice().reverse().forEach(d => {
        if (!seen.has(d.id)) items.unshift(d)
      })
      await nextTick()
      listRef.value.scrollTop = beforeT + (listRef.value.scrollHeight - beforeH)
    } else {
      normalized.forEach(d => {
        if (!seen.has(d.id)) items.push(d)
      })
    }
  } catch (e) {
    error.value = e
  }
}


/* ---------- 初期ロード (今日〜+3日) ---------- */
onMounted(async ()=>{
	await fetchRange(oldest, newest)
	initFutureObserver()
	initPullToRefresh()
})

/* ---------- Pull to Refresh 本体 ---------- */
function initPullToRefresh(){
	let startY = 0
	let active = false

	const threshold = 60	// 60px 以上で発火

	function onDown(e){
		if(listRef.value.scrollTop !== 0) return	// 上端でない
		active = true
		startY = e.touches ? e.touches[0].clientY : e.clientY
	}
	function onMove(e){
		if(!active) return
		const y = e.touches ? e.touches[0].clientY : e.clientY
		const dist = Math.max(0, y - startY)
		if(dist===0) return
		isPulling.value = true
		pullDistance.value = dist > 120 ? 120 : dist	// キャップ
		e.preventDefault()								// 画面をスクロールさせない
	}
	async function onUp(){
		if(!active) return
		active = false
		if(pullDistance.value >= threshold){
			await loadPast()
		}
		// reset
		isPulling.value = false
		pullDistance.value = 0
	}

	const el = listRef.value
	el.addEventListener('touchstart', onDown, { passive:true })
	el.addEventListener('touchmove',	onMove, { passive:false })
	el.addEventListener('touchend',		onUp)
	el.addEventListener('mousedown',	onDown)
	el.addEventListener('mousemove',	onMove)
	window.addEventListener('mouseup',	onUp)
}

/* ---------- 過去 3 日読み込み ---------- */
async function loadPast(){
	if(loadingPast.value) return
	loadingPast.value = true
	const newOld = oldest.subtract(3,'day')
	await fetchRange(newOld, oldest.subtract(1,'day'), true)
	oldest = newOld
	loadingPast.value = false
}

/* ---------- 未来側 IntersectionObserver ---------- */
const bottomSentinel = ref(null)
function initFutureObserver(){
	const io = new IntersectionObserver(async ([entry])=>{
		if(entry.isIntersecting && !loadingFuture.value){
			loadingFuture.value = true
			const newNew = newest.add(3,'day')
			await fetchRange(newest.add(1,'day'), newNew)
			newest = newNew
			loadingFuture.value = false
		}
	},{ threshold:0.01 })
	io.observe(bottomSentinel.value)
}

/* ---------- 日付ごとにまとめた配列 ---------- */
const groups = computed(() => {
  const map = new Map()
  for (const r of items) {
    const key = dayjs(r.start_at).format('YYYY-MM-DD')
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(r)
  }
  return Array.from(map.entries()).map(([key, list]) => ({
    date: dayjs(key),
    list
  }))
})

/* ---------- 親の selectedDate 変更 ---------- */
watch(() => props.selectedDate, async d => {
  if (!d) return
  if (d.isBefore(oldest)) {
    await fetchRange(d.clone().subtract(3, 'day'), oldest, true)
    oldest = d.clone().subtract(3, 'day')
  }
  if (d.isAfter(newest)) {
    await fetchRange(newest.add(1, 'day'), d.clone().add(3, 'day'))
    newest = d.clone().add(3, 'day')
  }
  nextTick(() => {
    document.getElementById(`date-${d.format('YYYYMMDD')}`)
      ?.scrollIntoView({ block: 'start' })
  })
})


/* ---------- Google Static Map ---------- */
const GMAP_KEY = import.meta.env.VITE_GMAP_KEY || ''
const mapImg  = a=> a
	? `https://maps.googleapis.com/maps/api/staticmap?center=${encodeURIComponent(a)}&zoom=15&size=100x100&markers=color:red|${encodeURIComponent(a)}&key=${GMAP_KEY}`
	: ''
const mapLink = a=> `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(a)}`

/* ---------- P2R 表示テキスト ---------- */
const pullText = computed(()=>{
	if(loadingPast.value) return '読み込み中…'
	if(pullDistance.value >= 60)	return '↑ 離して更新'
	return '↓ 過去 3 日を読み込む'
})

/* ---------- ルーター ----------*/
function openDetail(id){
  router.push(`${props.detailRoute}/${id}`)
}

</script>



<template>
	<!-- ▼ 過去を読むボタン（最上部） -->
		<!-- ▼ Pull to Refresh インジケーター -->
		<div class="pull-indicator text-center" :style="{ height:isPulling ? '40px':'0', transition:'height .2s' }">
			<span>{{ pullText }}</span>
		</div>

	<div v-if="error" class="text-danger p-3">通信エラー</div>

	<div v-else class="timeline--card" ref="listRef" :style="{ transform:`translateY(${pullDistance/2}px)` }">



		<div
			v-for="g in groups"
			:key="g.date.format('YYYYMMDD')"
			:id="`date-${g.date.format('YYYYMMDD')}`"
			class="wrapper"
		>
			<!-- ☆
			 	ここ、ある場合もない場合もこのdivがないと、表示が崩れちゃうみたい
				display grid 1fr 1frみたいにしちゃって
				ないとき、食い込んじゃう
				この場合どうしたらいい？☆
			-->
			<h6 class="card-date">
				<div class="month">
					<span>{{ g.date.format('M') }}月</span>
				</div>
				<div class="day">
					<span>{{ g.date.format('D') }}</span>
				</div>
				<div class="date">
					<span>{{ g.date.format('ddd') }}</span>
				</div>
			</h6>

			 <div v-for="r in g.list" :key="r.id" class="card">

				<div
					v-for="c in (r.casts ?? [])"
					:key="`${r.id}-${c.id}`"
					:class="{ settled: r.received_amount != null }"
				>
					<div class="card__wrap">
						<div class="cast-image" @click="openDetail(r.id)" style="cursor:pointer;">
							<div class="name">{{ c.stage_name }}様</div>

							<img :src="c.avatar_url" />

							<div class="time-area">
								<div class="start">{{ dayjs(r.start_at).format('M/D HH:mm') }}</div>
								<div class="time">{{ c.minutes }}分</div>
							</div>
						</div>

						<div class="info">

							<div class="other-area">

								<div class="area">

									<div v-if="r.customer_address" class="adress">
										{{ r.customer_address }}
									</div>

									<div v-if="(r.charges ?? []).some(ch=>ch.kind==='OPTION')" class="option">
										<span
											v-for="ch in (r.charges ?? []).filter(ch=>ch.kind==='OPTION')"
											:key="ch.id"
											class="badge bg-secondary me-1"
										>{{ ch.option_name }}</span>
									</div>
									<div v-else><span class="text-muted">オプションなし</span></div>
									<div class="customer">{{ r.customer_name }} 様</div>
								</div>

								<div v-if="r.customer_address" class="googlemap">
									<a :href="mapLink(r.customer_address)" target="_blank" rel="noopener">
										<img :src="mapImg(r.customer_address)" alt="map" class="img-fluid" />
									</a>
								</div>
								

							</div>
						</div>
					</div>


				</div>
			</div>
		</div>

		<!-- ↓方向ローディング -->
		<div style="height:80vh"></div>
		<div ref="bottomSentinel" style="height:1px"></div>
	</div>
</template>
