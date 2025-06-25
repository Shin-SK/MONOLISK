<!-- components/ReservationCard.vue ─ pickup 表示を修正 -->
<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({ reservation:Object })
const r = props.reservation

const casts   = computed(() => r.casts || [])
const opts	= computed(() =>
	(r.charges || []).filter(c => c.kind === 'OPTION')
)
</script>

<template>
<div class="card reservation-card">
	<div class="card-header d-flex justify-content-between">
		<span>#{{ r.id }}</span>
		<span>{{ new Date(r.start_at).toLocaleString() }}</span>
	</div>

	<div class="card-body d-flex gap-3">
		<!-- キャスト画像 -->
		<div class="d-flex flex-column align-items-center">
			<RouterLink	:to="`/reservations/${r.id}`"
						v-for="c in casts"
						:key="c.cast_profile"
						class="mb-2">
				<img	:src="c.avatar_url || '/static/img/cast-default.png'"
						class="border"
						style="width:56px;height:56px;object-fit:cover">
			</RouterLink>
		</div>

		<!-- 詳細 -->
		<div class="flex-grow-1">
			<p class="mb-1 fw-bold">
				{{ r.store_name }}
				/ {{ casts.map(c => c.stage_name).join(', ') }}
				({{ casts[0]?.minutes ?? '??' }}min)
			</p>

			<!-- 送迎住所 -->
			<p class="mb-1">
				<span v-if="r.pickup_address">
					送迎: {{ r.pickup_address }}
				</span>
				<span v-else class="text-muted">送迎住所はありません</span>
			</p>

			<!-- オプション -->
			<ul class="list-inline mb-1">
				<li v-if="!opts.length" class="list-inline-item text-muted">
					オプションはありません
				</li>
				<li v-else v-for="o in opts" :key="o.option" class="list-inline-item badge bg-secondary">
					{{ o.option_name || o.name }}
				</li>
			</ul>

			<p class="mb-0">
				金額: {{ r.expected_amount.toLocaleString() }} 円
			</p>
		</div>
	</div>
</div>
</template>
