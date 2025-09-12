// vite.config.js
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// ★ 追加
import Components from 'unplugin-vue-components/vite'
import Icons from 'unplugin-icons/vite'

import { fileURLToPath, URL } from 'node:url'
import { visualizer } from 'rollup-plugin-visualizer'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const HMR_HOST = env.VITE_HMR_HOST || ''
  const useTunnel = !!HMR_HOST

  // ★ Tabler 名→Iconify 名の“例外”があればここで上書き（足りたら空のままでOK）
  const TABLER_NAME_ALIASES = {
    // 例: HistoryToggle: 'history-toggle-off',
    // 例: FileNeutral: 'file'
  }

  return {
    plugins: [
      vue(),

      // ★ 追加: <IconXxx/> をビルド時に ~icons/tabler/xxx に解決
      Components({
        resolvers: [
          (name) => {
            if (!name.startsWith('Icon')) return
            const raw = name.slice(4) // 'Search', 'UserFilled', ...
            // PascalCase → kebab-case : 'UserFilled'→'user-filled'
            const kebab = raw.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()
            const finalName = TABLER_NAME_ALIASES[raw] || TABLER_NAME_ALIASES[kebab] || kebab
            // Iconify の仮想モジュール（既定エクスポート）を指す
            return { name: 'default', from: `~icons/tabler/${finalName}` }
          }
        ],
        dts: false, // ts使わないので生成なし
      }),

      // ★ 追加: アイコンの仮想モジュールを実体化
      Icons({ autoInstall: true }),

      // 既存
      VitePWA({
        registerType: 'autoUpdate',
        injectRegister: 'auto',
        devOptions: { enabled: mode === 'development', type: 'module' },
        includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
        workbox: {
          skipWaiting: true,
          clientsClaim: true,
          cleanupOutdatedCaches: true,
          navigateFallback: '/index.html',
          navigateFallbackDenylist: [/^\/api\//],
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
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      host: '0.0.0.0',
      proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
      allowedHosts: true,
      hmr: useTunnel ? { host: HMR_HOST, protocol: 'wss', clientPort: 443 } : undefined,
    },
    css: {
      devSourcemap: true,
      preprocessorOptions: { scss: { quietDeps: true } }
    }
  }
})
