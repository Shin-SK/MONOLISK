// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { visualizer } from 'rollup-plugin-visualizer'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      devOptions: { enabled: true },
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      workbox: {
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        maximumFileSizeToCacheInBytes: 6 * 1024 * 1024, // ★ 2MiB → 6MiB に拡張
        globIgnores: ['**/*.map'], // 任意: sourcemapはプリキャッシュ対象外
      },
      manifest: {
        name: 'MONOLISK',
        short_name: 'MONOLISK',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#111111',
        icons: [
          { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'any maskable' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
          { src: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png', purpose: 'any' }
        ]
      }
    }),
    visualizer({
      filename: 'report.html',
      open: true,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
	server: {
		host: true,           // iPhoneからアクセス可
		port: 5173,
		proxy: {
			'/api': {
				target: 'http://127.0.0.1:8000', // Django
				changeOrigin: true,
				// Django側のURLに /api が不要なら↓を有効化
				// rewrite: p => p.replace(/^\/api/, ''),
			},
			// 画像等をDjangoから直で出すなら必要に応じて
			// '/media': { target: 'http://127.0.0.1:8000', changeOrigin: true },
			// '/static': { target: 'http://127.0.0.1:8000', changeOrigin: true },
		},
	},
  css: {
    devSourcemap: true,
    preprocessorOptions: { scss: { quietDeps: true } }
  },
  // （任意）警告抑制や分割を少し入れるなら下記を有効化
  // build: {
  //   chunkSizeWarningLimit: 1500,
  //   rollupOptions: {
  //     output: {
  //       manualChunks: {
  //         vendor: ['vue','vue-router','pinia','axios','dayjs']
  //       }
  //     }
  //   }
  // }
})
