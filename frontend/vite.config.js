import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import {
  assertViteBuildApiBaseUrl,
  isProductionDeployEnv,
} from './src/services/apiBaseUrl.js'

export default defineConfig(({ mode }) => {
  // Load all env files for build-time validation (process.env wins over files).
  const fileEnv = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      react(),
      {
        name: 'enforce-api-base-url',
        configResolved(config) {
          if (config.command !== 'build') return

          const env = {
            ...fileEnv,
            ...config.env,
            ...process.env,
          }

          assertViteBuildApiBaseUrl({
            viteApiUrl: env.VITE_API_URL,
            isViteBuild: true,
            isProductionDeploy: isProductionDeployEnv(env),
          })
        },
      },
    ],
    server: {
      port: 3000,
      // Dev-only fallback if a relative /api request is made.
      // The Axios client normally uses absolute VITE_API_URL (port 8001).
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8001',
          changeOrigin: true,
        },
      },
    },
  }
})
