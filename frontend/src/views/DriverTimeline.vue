<!-- src/views/DriverTimeline.vue -->
<script setup>
import { ref }				 from 'vue'
import dayjs				 from 'dayjs'
import TimelineView			 from '@/components/TimelineView.vue'
import TaskListView			 from '@/components/TaskListView.vue'

import { RouterLink, useRouter } from 'vue-router'
import { api } from '@/api'
import { useUser } from '@/stores/useUser'

/* 選択日（初期＝今日） */
const selectedDate = ref(dayjs())
function handleDateChange(d){
	selectedDate.value = d		// 子から emit された日付を反映
}

/* 画面切替：'timeline' | 'list' */
const mode = ref('timeline')

const router	= useRouter()
const userStore	= useUser()
</script>

<template>
	<header class="header">
		<div class="header__wrap container">
			<div class="area">
				<div class="icon">
					<img :src="userStore.avatar" class="rounded-circle"/>
				</div>
			</div>

			<!-- ▼ mini-nav -->
			<div class="mini-nav">
				<button
					class="button"
					:class="mode==='list' ? 'btn btn-primary active' : 'btn btn-outline-primary'"
					@click="mode='list'">
					<span class="material-symbols-outlined">list</span>
				</button>

				<button
					class="button"
					:class="mode==='timeline' ? 'btn btn-primary active' : 'btn btn-outline-primary'"
					@click="mode='timeline'">
					<span class="material-symbols-outlined">view_timeline</span>
				</button>
			</div>
		</div>
	</header>

	<main class="flex-fill container">
		<component
			:is="mode==='timeline' ? TimelineView : TaskListView"
			class="flex-grow-1"
			:selected-date="selectedDate"
			@date-change="handleDateChange"	/><!-- ← TimelineView が emit -->
	</main>
</template>

<style scoped>
/* 既存スタイルそのままで OK */
</style>
