// vite.config.js
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { visualizer } from 'rollup-plugin-visualizer'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const HMR_HOST = env.VITE_HMR_HOST || ''       // ← .env.local から
  const useTunnel = !!HMR_HOST

  return {
    plugins: [
      vue(),
      VitePWA({
        registerType: 'autoUpdate',
        injectRegister: 'auto',
        devOptions: { enabled: mode === 'development', type: 'module' },
        includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
        workbox: {
          // 新SWを即アクティブ化＆即クライアント制御
          skipWaiting: true,
          clientsClaim: true,
          cleanupOutdatedCaches: true,
          navigateFallback: '/index.html',
          navigateFallbackDenylist: [/^\/api\//],
          maximumFileSizeToCacheInBytes: 6 * 1024 * 1024,
          globIgnores: ['**/*.map'],
          // API はキャッシュしない&Cookie通す（必要なら）
          runtimeCaching: [
            {
              urlPattern: ({url}) => url.origin.includes('monolisk') && url.pathname.startsWith('/api'),
              handler: 'NetworkOnly',
              options: { fetchOptions: { credentials: 'include' } }
            }
          ]
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
      visualizer({ filename: 'report.html', open: true, gzipSize: true, brotliSize: true }),
    ],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      host: '0.0.0.0',
      proxy: {
        '/api': { target: 'http://localhost:8000', changeOrigin: true },
      },
      // ★ 開発は全部許可でOK（トンネルのホスト替わっても触らない）
      allowedHosts: true,

      // ★ トンネル経由のHMRだけ環境変数で切り替え
      hmr: useTunnel
        ? { host: HMR_HOST, protocol: 'wss', clientPort: 443 }
        : undefined,
    },
    css: {
      devSourcemap: true,
      preprocessorOptions: { scss: { quietDeps: true } }
    }
  }
})
