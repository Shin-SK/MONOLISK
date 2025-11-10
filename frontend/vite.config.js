// vite.config.js
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// Icons / Components
import Components from 'unplugin-vue-components/vite'
import Icons from 'unplugin-icons/vite'

import { fileURLToPath, URL } from 'node:url'
import { visualizer } from 'rollup-plugin-visualizer'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const HMR_HOST = env.VITE_HMR_HOST || ''
  const useTunnel = !!HMR_HOST

  const TABLER_NAME_ALIASES = {}

  return {
    plugins: [
      vue(),

      Components({
        resolvers: [
          (name) => {
            if (!name.startsWith('Icon')) return
            const raw = name.slice(4)
            const kebab = raw.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()
            const finalName = TABLER_NAME_ALIASES[raw] || TABLER_NAME_ALIASES[kebab] || kebab
            return { name: 'default', from: `~icons/tabler/${finalName}` }
          }
        ],
        dts: false,
      }),

      Icons({ autoInstall: true }),

      // ← 手動登録に一本化（injectRegister を無効化）
      VitePWA({
        registerType: 'autoUpdate',
        injectRegister: null,
        devOptions: { enabled: mode === 'development', type: 'module' },
        includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
        workbox: {
          skipWaiting: true,
          clientsClaim: true,
          cleanupOutdatedCaches: true,
          navigateFallback: '/index.html',
          navigateFallbackDenylist: [/^\/api\//, /^\/manuals\//],
          maximumFileSizeToCacheInBytes: 6 * 1024 * 1024,
          globIgnores: ['**/*.map'],
          runtimeCaching: [
            {
              urlPattern: ({ url }) => url.pathname.startsWith('/api'),
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

    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },

    server: {
      host: '0.0.0.0',
      proxy: { '/api': { target: 'http://web:8000', changeOrigin: true } },
      allowedHosts: true,
      hmr: useTunnel ? { host: HMR_HOST, protocol: 'wss', clientPort: 443 } : undefined,
    },

    css: { devSourcemap: true, preprocessorOptions: { scss: { quietDeps: true } } }
  }
})