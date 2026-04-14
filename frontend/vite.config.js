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

      // PWA/SW 撤去フェーズ（リリース1）: 既存 SW を自殺させて剥がす
      // 次リリースで vite-plugin-pwa ごと削除予定
      VitePWA({
        selfDestroying: true,
        registerType: 'autoUpdate',
        injectRegister: 'auto',
        devOptions: { enabled: false },
      }),

      visualizer({ filename: 'report.html', open: true, gzipSize: true, brotliSize: true }),
    ],

    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },

    server: {
      host: '0.0.0.0',
      proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
      allowedHosts: true,
      hmr: useTunnel ? { host: HMR_HOST, protocol: 'wss', clientPort: 443 } : undefined,
    },

    css: { devSourcemap: true, preprocessorOptions: { scss: { quietDeps: true } } }
  }
})