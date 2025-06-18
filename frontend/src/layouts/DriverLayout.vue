<!-- src/components/Header.vue -->
<script setup>
import { useRouter } from 'vue-router'
import { computed } from 'vue'			// ★忘れずに
import { api } from '@/api'
import { useUser } from '@/stores/useUser'

const router	= useRouter()
const userStore	= useUser()

// yyyy/mm/dd
const today = computed(() => {
	const d = new Date()
	return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`
})

async function logout () {
	try {
		await api.post('dj-rest-auth/logout/')
	} finally {
		userStore.clear()
		router.push('/login')
	}
}
</script>

<template>
<div class="driver min-vh-100">

		<router-view />

</div>
</template>