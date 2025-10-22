import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: Number(env.VITE_DEV_SERVER_PORT ?? 5173),
      host: env.VITE_DEV_SERVER_HOST ?? '127.0.0.1',
      open: false,
      proxy: {
        '/api': {
          target: process.env.VITE_API_URL ?? 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path,
        },
      },
    },
    build: {
      sourcemap: false,
      outDir: 'dist',
      assetsDir: 'assets',
      chunkSizeWarningLimit: 600,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['vitest.setup.ts'],
      css: true,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov'],
        exclude: ['vitest.setup.ts', 'src/main.tsx'],
      },
    },
  }
})
