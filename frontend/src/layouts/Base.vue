<template>
	<div class="base">
		<div class="base-grid-wrapper">
			<aside class="aside">
					<div class="wrap">
						<NavigationMenu />
					</div>
					<footer class="footer">
						2025 MONOLISK (c)
					</footer>
			</aside>
			<div class="base-grid-wrapper__inner">
				<header class="header">
					<h1>MONOLISK</h1>
				</header>
				<main class="main">
					<router-view />
				</main>
			</div>
		</div>
	</div>
</template>

<script setup>
	import NavigationMenu from '@/components/NavigationMenu.vue'
</script>