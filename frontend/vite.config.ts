import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    // Prefer writable outDir; legacy root-owned ./dist may block emptyDir on some hosts.
    outDir: process.env.VITE_OUT_DIR || 'dist',
  },
  server: {
    port: 3000,
    host: true,
  },
})
